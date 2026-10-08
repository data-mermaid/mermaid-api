# Covariate fetching has been removed. This no-op stub remains for one release
# so update_site_covariates jobs already pickled into SQS before deploy can
# still be unpickled and drained by the worker. Delete with the Covariate model.


def update_site_covariates(site):
    pass
