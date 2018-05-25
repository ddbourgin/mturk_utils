#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import logging
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter

import pexpect

DESCRIPTION = """
Emulate TurkPrime's HyperBatch feature to avoid accruing an extra 20% MTurk fee
for having more than 9 subjects / HIT. Based on Dave Eargle's
`psiturk_batcher.sh` script.

Note: Before running this script, make sure that `launch_in_sandbox_mode =
false` in the psiturk config.txt so that it creates live HITs.

Usage
-----
Place in the same directory as the experiment's `config.txt` and run
    >>> psiturk_batcher.py <N. assignments to post> <Reward per assignment> <Assignment duration>
"""


class CustomFormatter(ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter):
    pass


logger = logging.getLogger()

# create a handler for printing to logfile
logfile_handler = logging.FileHandler('psiturk_batcher.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logfile_handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)

# create additional handler for printing to stdout
stdout_handler = logging.StreamHandler(sys.stdout)
formatter_stdout = logging.Formatter('%(message)s')
stdout_handler.setFormatter(formatter_stdout)
stdout_handler.setLevel(logging.DEBUG)

logger.addHandler(logfile_handler)
logger.addHandler(stdout_handler)

# hacky methods to permit us to use loggers with pexpect
# https://mail.python.org/pipermail/python-list/2010-March/570847.html
def _write(*args, **kwargs):
    content = args[0].decode('utf-8')
    for eol in ['\r\n', '\r', '\n']:
        content = re.sub('\{}$'.format(eol), '', content)
    return logger.info(content)


def _doNothing():
    pass

# give the logger the methods required by pexpect
logger.write = _write
logger.flush = _doNothing


def create_hit(n_assignments, reward, duration):
    logger.info('Creating a HIT with %s assignments' % n_assignments)

    cmd = '"hit create {:.0f} {:.2f} {:.2f}"'.format(
        n_assignments, reward, duration)

    command = ['psiturk', '-e', cmd]
    logger.info('> ' + ' '.join(command))

    pexpect.run(" ".join(command), logfile=logger)
    return True


if __name__ == "__main__":
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter)

    parser.add_argument(
        "n_assignments",
        type=int,
        help="total number of assignments to post")

    parser.add_argument(
        "reward",
        type=float,
        help="reward (in USD) for completing a HIT")

    parser.add_argument(
        "duration",
        type=float,
        help="maximum amount of time (in hours) allowed to complete the HIT")

    parser.add_argument(
        "-m",
        "--max_assignments",
        default=9,
        type=int,
        help="maximum number of assignments for any individual HIT")

    parser.add_argument(
        "-s",
        "--sleep_time",
        default=5,
        type=int,
        help="time (in seconds) to sleep before posting a new batch")

    args = parser.parse_args()

    TOTAL_ASSIGNMENTS = args.n_assignments
    SPACING = args.sleep_time
    HIT_REWARD = args.reward
    HIT_DURATION = args.duration
    MAX_ASSIGNMENTS_PER_HIT = args.max_assignments

    if HIT_REWARD <= 0:
        raise ValueError(
            'Invalid reward amount: {} USD'.format(HIT_REWARD))
    if HIT_DURATION <= 0:
        raise ValueError(
            'Invalid HIT duration: {} hours'.format(HIT_DURATION))
    if TOTAL_ASSIGNMENTS <= 0:
        raise ValueError(
            'Invalid number of assignments: {}'.format(TOTAL_ASSIGNMENTS))

    # derived variables
    total_time = 60
    n_rounds = int(total_time / SPACING)
    assignments_per_round = int(TOTAL_ASSIGNMENTS / n_rounds)
    total_assignments_wo_mod = n_rounds * assignments_per_round
    assignments_remainder = TOTAL_ASSIGNMENTS % total_assignments_wo_mod

    logger.info(
        "Total time: %s seconds" % total_time)
    logger.info(
        "Spacing: %s seconds" % SPACING)
    logger.info(
        "Total assignments: %s" % TOTAL_ASSIGNMENTS)
    logger.info(
        "Assignments per round (ignoring modulus): %s" % assignments_per_round)
    logger.info(
        "Assignments remainder to distribute: %s" % assignments_remainder)
    logger.info(
        "Number of rounds: %s" % n_rounds)

    confirm = input('\nContinue? [y/N] ').lower()
    while confirm not in ['n', 'no', 'yes', 'y']:
        confirm = input('Continue? [y/N] ').lower()

    if confirm in ['n', 'no']:
        logger.info('Exiting...')
        sys.exit()

    for rr in range(1, n_rounds + 1):
        logger.info("\n")
        logger.info("ROUND {}".format(rr))
        n_assignments_this_round = assignments_per_round

        if rr <= assignments_remainder:
            n_assignments_this_round += 1

        n_hits_this_round = int(
            n_assignments_this_round / MAX_ASSIGNMENTS_PER_HIT)
        n_assignments_for_mod_hit = n_assignments_this_round % MAX_ASSIGNMENTS_PER_HIT

        logger.info(
            "TOTAL assignments for this round: %s" % n_assignments_this_round)

        for hit in range(n_hits_this_round):
            proc = create_hit(MAX_ASSIGNMENTS_PER_HIT, HIT_REWARD,
                              HIT_DURATION)

        if n_assignments_for_mod_hit > 0:
            create_hit(n_assignments_for_mod_hit, HIT_REWARD, HIT_DURATION)

        logger.info("Sleeping for %s seconds..." % SPACING)
        time.sleep(SPACING)

    logger.info("Finished!")
