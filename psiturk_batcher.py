#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import logging
from subprocess import Popen, PIPE, STDOUT
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter

DESCRIPTION = \
    """
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
handler = logging.FileHandler('psiturk_batcher.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)

# add additional handler for printing to stdout
stdout_handler = logging.StreamHandler(sys.stdout)
formatter_stdout = logging.Formatter('%(message)s')
stdout_handler.setFormatter(formatter_stdout)
stdout_handler.setLevel(logging.DEBUG)

logger.addHandler(handler)
logger.addHandler(stdout_handler)


def create_hit(n_assignments, reward, duration):
    logger.INFO('Creating a hit with %s assignments' % n_assignments)
    proc = Popen(
        ['psiturk', '-e', 'hit', 'create', n_assignments, reward, duration],
        stdout=PIPE,
        stderr=STDOUT,
        shell=True)
    output, err = proc.communicate()

    if err:
        logger.INFO('Error posting HIT!')
        logger.INFO(err.decode('utf-8'))
        sys.exit()
    else:
        logger.INFO(output.decode('utf-8'))
    return proc


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
        raise ValueError('Invalid reward amount: {} USD'.format(HIT_REWARD))
    if HIT_DURATION <= 0:
        raise ValueError('Invalid HIT duration: {} hours'.format(HIT_DURATION))
    if TOTAL_ASSIGNMENTS <= 0:
        raise ValueError(
            'Invalid number of assignments: {}'.format(TOTAL_ASSIGNMENTS))

    # derived variables
    total_time = 60
    n_rounds = total_time / SPACING
    assignments_per_round = TOTAL_ASSIGNMENTS / n_rounds
    total_assignments_wo_mod = n_rounds * assignments_per_round
    assignments_remainder = TOTAL_ASSIGNMENTS % total_assignments_wo_mod

    logger.INFO("Total time: %s seconds" % total_time)
    logger.INFO("Spacing: %s seconds" % SPACING)
    logger.INFO("Total assignments: %s" % TOTAL_ASSIGNMENTS)
    logger.INFO("Assignments per round (ignoring modulus): %s" %
                total_assignments_wo_mod)
    logger.INFO("Assignments remainder to distribute: %s" %
                assignments_remainder)
    logger.INFO("Number of rounds: %s" % n_rounds)

    confirm = input('\nContinue? [y/N] ').lower()
    while confirm not in ['n', 'no', 'yes', 'y']:
        confirm = input('\nContinue? [y/N] ').lower()

    if confirm in ['n', 'no']:
        sys.exit()

    for rr in range(1, n_rounds + 1):
        logger.INFO("ROUND {}".format(rr))
        n_assignments_this_round = assignments_per_round

        if rr <= assignments_remainder:
            n_assignments_this_round += 1

        n_hits_this_round = n_assignments_this_round / MAX_ASSIGNMENTS_PER_HIT
        n_assignments_for_mod_hit = n_assignments_this_round % MAX_ASSIGNMENTS_PER_HIT
        logger.INFO("TOTAL assignments for this round: %s" %
                    n_assignments_this_round)

        for hit in range(n_hits_this_round):
            proc = create_hit(MAX_ASSIGNMENTS_PER_HIT, HIT_REWARD,
                              HIT_DURATION)

        if n_assignments_for_mod_hit > 0:
            proc = create_hit(n_assignments_for_mod_hit,
                              HIT_REWARD, HIT_DURATION)

        logger.INFO('Sleeping for %s seconds...' % SPACING)
        time.sleep(SPACING)

    logger.INFO('Finished!')
