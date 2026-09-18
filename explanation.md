# Benthic PIT interval validation: what the errors mean

## What a PIT survey is

You lay a 30 m tape along the reef and record what is underneath every 0.25 m, which gives 120
points. "Interval start" says where the first point goes.

## The two ways people label those points

```
Label by the END of each segment:    0.25  0.50 ... 30.00   (120 points)
Label by the START of each segment:  0.00  0.25 ... 29.75   (120 points)
```

Same dive, same data, different numbering. It is like counting floors from the ground floor or from
floor one.

## The three checks that run, and how strict each one is

| check | what it expects | slack allowed |
| --- | --- | --- |
| **How many?** | length / interval size = 120 observations. **Ignores where you started.** | plus or minus 1 observation |
| **Any gaps?** | builds the expected positions as *start, start + 0.25, ...* and keeps going **until it reaches the tape's end**, then requires every one to be present | none on the count; 0.0001 m for rounding |
| **On the grid?** | every recorded position sits on *start + a whole number of intervals*, and none is before the start | 0.0001 m for rounding |

## Where the logic breaks

Checks 1 and 2 disagree about how long the survey is, because check 1 ignores the start and check 2
does not. They only agree when the start happens to equal the interval size, which is the default,
which is why nobody noticed.

For a file that starts at 0:

- Check 1 wants 120 observations. The file has 120. **Passes.**
- Check 2 counts from 0 and runs to the end of the tape, so it expects 121 positions,
  `0.00 ... 30.00`. **Fails**, reporting 30.00 as missing data that was never collected.
- Check 3 compared against the wrong start, because that setting was lost during an earlier upload,
  so it also flagged the point at 0 as "before the start".

Check 2 has no slack on the count, so a one position disagreement is a hard failure. Check 1's
plus or minus 1 slack is what hides the same disagreement elsewhere.

A side effect of check 1 ignoring the start: a survey starting at 1 m with 120 points runs to
30.75 m, which is three quarters of a metre past the end of the tape, and it passes every check.
Meanwhile the correct 117 point version of that same survey fails.

## Why this needs a protocol decision

The existing database contains all of these patterns:

| pattern | approximate records |
| --- | --- |
| start at 0, include both ends (121 points) | 2,400 |
| start at 0, stop one short (120 points) | 1,500 |
| start at 1 m or more | 470 |

So tightening the checks is not only a code fix. Whichever pattern is declared correct, the others
become invalid. That is a call for whoever owns the survey protocol.
