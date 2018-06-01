#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter, ArgumentDefaultsHelpFormatter

import boto3
import numpy as np

DESCRIPTION = """
Approve workers for an individual HIT.

Usage
-----
    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> approve_hit.py <HIT ID>
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


def credit_hit(client, hit_id, credited_workers=set(), credited_assignments=set()):
    assignments = client.list_assignments_for_hit(
        HITId=hit_id,
        MaxResults=100,
        AssignmentStatuses=['Submitted']
    )

    for ass in assignments['Assignments']:
        ass_id = ass['AssignmentId']
        worker_id = ass['WorkerId']
        print('\tCrediting worker {} on assignment {}'
              .format(worker_id, ass_id))

        _ = client.approve_assignment(
            AssignmentId=ass_id,
            RequesterFeedback='Thank you for completing our experiment!',
            OverrideRejection=False
        )

        credited_workers.add(worker_id)
        credited_assignments.add(ass_id)
    return credited_workers, credited_assignments


def load_roster():
    credited_hits = set()
    credited_workers = set()
    credited_assignments = set()
    if os.path.lexists('credited.npz'):
        credited = np.load('credited.npz')
        credited_hits = set(credited['credited_hits'])
        credited_workers = set(credited['credited_workers'])
        credited_assignments = set(credited['credited_assignments'])
    return credited_hits, credited_workers, credited_assignments


if __name__ == "__main__":
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter)

    parser.add_argument(
        'hit_id',
        metavar="ID",
        type=str,
        help="The HIT ID")

    args = parser.parse_args()

    # try loading the info on already-credited HIT from previous runs
    credited_hits, credited_workers, credited_assignments = load_roster()

    client = mturk_client()

    try:
        hit = client.get_hit(HITId=args.hit_id)['HIT']
    except KeyError:
        print('Could not find HIT ID `{}`'.format(args.hit_id))
        sys.exit()

    already_done = hit['HITId'] in credited_hits

    if not already_done:
        print('Collecting workers for HIT {}, title: `{}`'
              .format(hit['HITId'], hit['Title']))

        credited_workers, credited_assignments = credit_hit(
            client, hit['HITId'], credited_workers, credited_assignments)

        credited_hits.add(hit['HITId'])

        np.savez(
            'credited.npz',
            credited_hits=np.array(list(credited_hits)),
            credited_workers=np.array(list(credited_workers)),
            credited_assignments=np.array(list(credited_assignments)),
        )
