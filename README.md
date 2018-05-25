# mturk utils
Convenience scripts for interacting with MTurk/Psiturk. 

Before using the scripts below, define the following environment variables:

    > export AWS_ACCESS_KEY_ID=<your MTurk access key id>
    > export AWS_SECRET_ACCESS_KEY=<your MTurk secret access key>


## approve_batch.py
**Usage:** `approve_batch.py [-h] [-t TITLE]`

Batch HIT approver. Only approves HITs that are listed as reviewable,
saving a log of subject and HIT IDs that it approves to the current directory in an `.npz` archive. Can be run multiple times as more HITs are posted.

#### Optional arguments
  - `-h`, `--help`            show help message and exit
  - `-t TITLE`, `--title TITLE` title of the experiment/HIT (default: None)
  
## assign_qualification.py
**Usage:** `assign_qualification.py [-h] [--value VALUE] QUALIFICATION [WORKER [WORKER ...]]`

Assign a qualification to a given worker ID/IDs. Useful for setting up
invitation-only makeup HITs.

#### Positional arguments
  - `QUALIFICATION`  qualification ID
  - `WORKER`         worker ID (default: None)

#### Optional arguments
  - `-h`, `--help`     show help message and exit
  - `--value VALUE`  qualification value (default: 1)
  
## create_qualification.py
**Usage:** `create_qualification.py [-h] NAME DESCRIPTION`

Create a new worker qualification. Useful in preparation for making
invitation-only makeup HITs.

#### Positional arguments
  - `NAME`         name of the new qualification. used to represent the
               qualification to workers
  - `DESCRIPTION`  long description for the qualification. this is displayed when
               a worker examines the qualification

#### Optional arguments
  - `-h`, `--help`   show help message and exit

## psiturk_batcher.py
**Usage:** `psiturk_batcher.py [-h] [-m MAX_ASSIGNMENTS] [-s SLEEP_TIME] n_assignments reward duration`

Emulate TurkPrime's HyperBatch feature to avoid accruing an extra 20% MTurk fee
for having more than 9 subjects / HIT. Based on Dave Eargle's `psiturk_batcher.sh` script.

Note: Before running this script, make sure that `launch_in_sandbox_mode =
false` in the psiturk config.txt so that it creates live HITs!

#### Usage
Place in the same directory as the experiment's `config.txt`.

#### Positional arguments
  - `n_assignments`         total number of assignments to post
  - `reward`                reward (in USD) for completing a HIT
  - `duration`              maximum amount of time (in hours) allowed to complete
                        the HIT

#### Optional arguments
  - `-h`, `--help`            show help message and exit
  - `-m MAX_ASSIGNMENTS`, `--max_assignments MAX_ASSIGNMENTS`
                        maximum number of assignments for any individual HIT
                        (default: 9)
  - `-s SLEEP_TIME`, `--sleep_time SLEEP_TIME`
                        time (in seconds) to sleep before posting a new batch
                        (default: 5)
