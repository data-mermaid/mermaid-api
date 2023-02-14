SimpleQ
-------

Modified version of [SimpleQ](https://github.com/rdegges/simpleq/blob/master/simpleq/queues.py).  Updated to work with python3 and boto3.


## DJANGO SETTINGS OPTIONS

- message batch size
- number of seconds to wait in seconds for new messages
- sqs visibility timeout

**Max number of messages to fetch in one call.**

`SQS_BATCH_SIZE = 10  # default`

**Number of seconds to wait in seconds for new messages. If there are messages ready to be processed, then the receiver will not wait this long.**

`SQS_WAIT_SECONDS = 20  # default`

**Number of seconds before the message is visible again in SQS for other tasks to pull.**

`SQS_MESSAGE_VISIBILITY = 300  # default`

**Name of queue, if it doesn't exist it will be created.**

`QUEUE_NAME = "<Q>"  # required`
