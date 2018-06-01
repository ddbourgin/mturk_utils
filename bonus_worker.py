#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter, ArgumentDefaultsHelpFormatter

import boto3
import numpy as np

DESCRIPTION = """
Bonus a worker.

Usage
-----
    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> bonus_worker.py <HIT ID>
"""


class CustomFormatter(ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter):
    pass


def all_pages(func, **kwargs):
    """Handle pagination for boto3 AWS requests"""
    response = func(**kwargs)
    pages = [response]
    while response['NumResults'] > 0:
        response = func(
            NextToken=response['NextToken'],
            **kwargs
        )
        pages += [response]
    return pages


def mturk_client():
    print("Connecting to mechanical turk...")
    key_id = os.environ['AWS_ACCESS_KEY_ID']
    key = os.environ['AWS_SECRET_ACCESS_KEY']

    client = boto3.client(
        'mturk',
        aws_access_key_id=key_id,
        aws_secret_access_key=key
    )
    return client


def bonus_worker(client, args, bonused_workers=set(), bonused_assignments=set()):
    assignments = client.list_assignments_for_hit(
        HITId=args.hit,
        MaxResults=100
    )

    for ass in assignments['Assignments']:
        ass_id = ass['AssignmentId']
        worker_id = ass['WorkerId']

        if worker_id == args.worker:
            print('\tBonusing worker {} on assignment {} with ${:.2f}'
                  .format(args.worker, ass_id, args.bonus))

            _ = client.send_bonus(
                WorkerId=args.worker,
                BonusAmount='{:.2f}'.format(args.bonus),
                AssignmentId=ass_id,
                Reason='Bonus for Gambling Experiment'
            )

            bonused_workers.add(worker_id)
            bonused_assignments.add(ass_id)
    return bonused_workers, bonused_assignments


def load_roster():
    bonused_workers = set()
    bonused_assignments = set()
    if os.path.lexists('bonused.npz'):
        bonused = np.load('bonused.npz')
        bonused_workers = set(bonused['bonused_workers'])
        bonused_assignments = set(bonused['bonused_assignments'])
    return bonused_workers, bonused_assignments


if __name__ == "__main__":
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter)

    parser.add_argument(
        'worker',
        type=str,
        metavar="WORKER_ID",
        help="The worker ID")

    parser.add_argument(
        'hit',
        type=str,
        metavar="HIT_ID",
        help="The HIT ID")

    parser.add_argument(
        'bonus',
        type=float,
        metavar="BONUS",
        help="The amount to bonus the worker (in USD)")

    args = parser.parse_args()

    # try loading the info on already-bonused HIT from previous runs
    bonused_workers, bonused_assignments = load_roster()

    client = mturk_client()

    try:
        hit = client.get_hit(HITId=args.hit)['HIT']
    except KeyError:
        print('Could not find HIT ID `{}`'.format(args.hit))
        sys.exit()

    already_done = args.worker in bonused_workers

    if not already_done:
        bonused_workers, bonused_assignments = bonus_worker(
            client, args, bonused_workers, bonused_assignments)

        np.savez(
            'bonused.npz',
            bonused_workers=np.array(list(bonused_workers)),
            bonused_assignments=np.array(list(bonused_assignments)),
        )
