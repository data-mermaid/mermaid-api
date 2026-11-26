# Ignore chosen validation warnings on your Collecting records, then (optionally) submit.
#
# MERMAID supports sending ignores through its API, but does not offer bulk ignoring
# in Collect or mermaidr. Ignoring warnings in bulk is your choice, made at the expense
# of data quality: an ignore normally means a person reviewed that warning on that
# record and accepted it, and data submitted this way looks the same as data reviewed
# record by record. Only ignore warnings you have decided are expected for your data.
#
# What this does, for one project, on the records YOU own in Collecting:
#   1. Validates records that have never been validated or have changed since.
#   2. For records with warnings, sets each warning whose code is in `codes` to
#      "ignore". Errors and other warnings are left alone.
#   3. Saves those records and validates them again.
#   4. If submit = TRUE, submits every record that now validates "ok", then repeats,
#      because submitting can create new warnings on other records (e.g.
#      similar_date_sample_unit), until a pass changes nothing.
# Records with errors or other warnings stay in Collecting for review in Collect.
#
# Requirements: httr, jsonlite, and mermaidr (for sign-in), e.g.
#   install.packages(c("httr", "jsonlite")); remotes::install_github("data-mermaid/mermaidr")
#
# Usage:
#   source("ignore_warnings.R")
#   # 1. See what would happen; changes nothing:
#   ignore_warnings("<project id>", codes = c("too_few_observations", "low_density"))
#   # 2. Ignore those warnings and validate:
#   ignore_warnings("<project id>", codes = c(...), dry_run = FALSE)
#   # 3. Same, and submit what becomes valid (repeats until nothing changes):
#   ignore_warnings("<project id>", codes = c(...), dry_run = FALSE, submit = TRUE)
#
# Sign-in: uses mermaidr's login (mermaidr::mermaid_token()). To use a MERMAID API key
# instead, set the MERMAID_API_KEY environment variable. MERMAID_API_URL overrides the
# API address (default https://api.datamermaid.org/v1).

library(httr)
library(jsonlite)

api_url <- function() sub("/+$", "", Sys.getenv("MERMAID_API_URL", "https://api.datamermaid.org/v1"))

auth_config <- function() {
  key <- Sys.getenv("MERMAID_API_KEY")
  if (nzchar(key)) {
    return(add_headers(Authorization = paste("Bearer", key)))
  }
  mermaidr::mermaid_token()
}

mermaid_call <- function(method, path, body = NULL) {
  url <- if (startsWith(path, "http")) path else paste0(api_url(), "/", path)
  json <- if (is.null(body)) NULL else toJSON(body, auto_unbox = TRUE, null = "null", digits = NA)
  for (attempt in 1:5) {
    res <- VERB(method, url, auth_config(), content_type_json(), accept_json(),
                user_agent("ignore_warnings.R"), body = json)
    if (!status_code(res) %in% c(429, 502, 503, 504)) break
    wait <- suppressWarnings(as.numeric(headers(res)[["retry-after"]]))
    Sys.sleep(if (length(wait) == 1 && !is.na(wait)) wait else 2^attempt)
  }
  text <- content(res, as = "text", encoding = "UTF-8")
  if (http_error(res)) {
    stop(sprintf("%s %s failed (%s): %s", method, url, status_code(res), substr(text, 1, 500)), call. = FALSE)
  }
  # simplifyVector = FALSE keeps the JSON structure exactly, so it can be sent back unchanged.
  fromJSON(text, simplifyVector = FALSE)
}

# All of your collect records in the project (the API only returns your own).
list_collect_records <- function(project, protocol = NULL) {
  out <- list()
  page <- mermaid_call("GET", sprintf("projects/%s/collectrecords/?limit=100", project))
  repeat {
    out <- c(out, page$results)
    if (is.null(page[["next"]])) break
    page <- mermaid_call("GET", page[["next"]])
  }
  if (!is.null(protocol)) {
    out <- Filter(function(r) identical(r$data$protocol, protocol), out)
  }
  out
}

record_status <- function(record) {
  s <- record$validations$status
  if (is.null(s)) NA_character_ else s
}

is_result <- function(x) is.list(x) && !is.null(x$validation_id) && !is.null(x$status)

# Every individual validation result, wherever it sits in the results tree
# (record-level under "$record", per field, or per observation).
all_results <- function(node) {
  if (is_result(node)) return(list(node))
  if (is.list(node)) return(do.call(c, c(list(list()), lapply(node, all_results))))
  list()
}

# Set warnings with a chosen code to "ignore"; returns the new tree and how many changed.
ignore_in_tree <- function(node, codes) {
  if (is_result(node)) {
    if (identical(node$status, "warning") && isTRUE(node$code %in% codes)) {
      node$status <- "ignore"
      return(list(node = node, n = 1L))
    }
    return(list(node = node, n = 0L))
  }
  if (is.list(node) && length(node) > 0) {
    n <- 0L
    for (i in seq_along(node)) {
      r <- ignore_in_tree(node[[i]], codes)
      if (r$n > 0) node[[i]] <- r$node
      n <- n + r$n
    }
    return(list(node = node, n = n))
  }
  list(node = node, n = 0L)
}

validate_ids <- function(project, ids, batch_size = 3) {
  statuses <- character(0)
  for (batch in split(ids, ceiling(seq_along(ids) / batch_size))) {
    res <- mermaid_call("POST", sprintf("projects/%s/collectrecords/validate/", project),
                        list(ids = as.list(batch)))
    statuses <- c(statuses, vapply(res, function(x) x$status, ""))
  }
  statuses
}

submit_id <- function(project, id) {
  res <- mermaid_call("POST", sprintf("projects/%s/collectrecords/submit/", project), list(ids = list(id)))
  res[[id]]$status
}

summarise_codes <- function(records, status) {
  codes <- unlist(lapply(records, function(r) {
    vapply(Filter(function(x) identical(x$status, status), all_results(r$validations$results)),
           function(x) if (is.null(x$code)) NA_character_ else x$code, "")
  }))
  if (length(codes) == 0) {
    message("  (none)")
    return(invisible(NULL))
  }
  print(sort(table(codes), decreasing = TRUE))
}

ignore_warnings <- function(project, codes, protocol = NULL, dry_run = TRUE, submit = FALSE,
                            max_passes = 10) {
  stopifnot(is.character(codes), length(codes) > 0)
  started <- Sys.time()
  totals <- c(ignored = 0L, submitted = 0L)

  for (pass in seq_len(max_passes)) {
    records <- list_collect_records(project, protocol)
    message(sprintf("Pass %d: %d of your records in Collecting.", pass, length(records)))
    if (length(records) == 0) break

    # 1. Validate records that have no current validation (never validated, or edited since).
    needs_validation <- vapply(records, function(r) is.na(record_status(r)) || record_status(r) == "stale", TRUE)
    if (any(needs_validation)) {
      ids <- vapply(records[needs_validation], function(r) r$id, "")
      if (dry_run) {
        message(sprintf("  %d records need validating first; run with dry_run = FALSE (or mermaid_import_bulk_validate()).", length(ids)))
      } else {
        message(sprintf("  Validating %d records (~%d s)...", length(ids), ceiling(length(ids) / 3)))
        validate_ids(project, ids)
        records <- list_collect_records(project, protocol)
      }
    }

    # 2. Ignore chosen warnings.
    changed <- character(0)
    would_be_ok <- 0L
    for (r in Filter(function(r) identical(record_status(r), "warning"), records)) {
      res <- ignore_in_tree(r$validations$results, codes)
      if (res$n == 0) next
      left <- vapply(all_results(res$node), function(x) x$status %in% c("warning", "error"), TRUE)
      if (!any(left)) would_be_ok <- would_be_ok + 1L
      totals["ignored"] <- totals["ignored"] + res$n
      if (!dry_run) {
        r$validations$results <- res$node
        mermaid_call("PATCH", sprintf("projects/%s/collectrecords/%s/", project, r$id),
                     list(project = project, validations = r$validations))
      }
      changed <- c(changed, r$id)
    }

    if (dry_run) {
      message(sprintf("  Would ignore %d warnings on %d records; %d of them would then have no warnings or errors.",
                      totals["ignored"], length(changed), would_be_ok))
      message("  Open warnings and errors across your records, by code:")
      message("  warnings:"); summarise_codes(records, "warning")
      message("  errors:"); summarise_codes(records, "error")
      return(invisible(NULL))
    }

    # 3. Validate the changed records again.
    if (length(changed) > 0) {
      message(sprintf("  Ignored warnings on %d records; validating them again (~%d s)...",
                      length(changed), ceiling(length(changed) / 3)))
      validate_ids(project, changed)
    }

    if (!submit) break

    # 4. Submit everything that is now ok.
    records <- list_collect_records(project, protocol)
    ok_ids <- vapply(Filter(function(r) identical(record_status(r), "ok"), records), function(r) r$id, "")
    n_submitted <- 0L
    if (length(ok_ids) > 0) {
      message(sprintf("  Submitting %d valid records (~%d s)...", length(ok_ids), length(ok_ids)))
      for (id in ok_ids) {
        if (identical(submit_id(project, id), "ok")) n_submitted <- n_submitted + 1L
      }
    }
    totals["submitted"] <- totals["submitted"] + n_submitted
    message(sprintf("  Submitted %d of %d.", n_submitted, length(ok_ids)))

    if (length(changed) == 0 && n_submitted == 0) break
  }

  records <- list_collect_records(project, protocol)
  message(sprintf("Done in %s. Ignored %d warnings; submitted %d records. %d records remain in Collecting.",
                  format(round(difftime(Sys.time(), started), 1)), totals["ignored"], totals["submitted"],
                  length(records)))
  if (length(records) > 0) {
    message("Still open on those records (review in Collect):")
    message("warnings:"); summarise_codes(records, "warning")
    message("errors:"); summarise_codes(records, "error")
  }
  invisible(totals)
}
