#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter, ArgumentDefaultsHelpFormatter

import boto3
import numpy as np

DESCRIPTION = \
    """
Batch HIT approver for psiturk. Only approves HITS that are listed as reviewable,
saving a log of subject and HIT IDs that it approves (to guard against double
payments, etc.) Script can be run multiple times as more HITs are posted.

Usage
-----
Place in the same directory as the experiment's `config.txt`, or pass the title of
the HIT as an optional argument at the command line

    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> approve.py -t <HIT title>
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


def credit_hit(hit_id, credited_workers=set(), credited_assignments=set()):
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
        '-t',
        "--title",
        metavar="TITLE",
        type=str,
        help="title of the experiment/HIT.")

    args = parser.parse_args()
    HIT_TITLE = args.title

    # if HIT title is not specified at the command line, try to load it from
    # the psiturk config.txt
    if not HIT_TITLE:
        if not os.path.lexists('config.txt'):
            raise FileNotFoundError(
                'Cannot find `config.txt` file in the current directory')

        with open('config.txt', 'r') as handle:
            for line in handle:
                if line.startswith('title'):
                    HIT_TITLE = line.split('=')[-1].strip()

    # try loading the info on already-credited HIT from previous runs
    credited_hits, credited_workers, credited_assignments = load_roster()

    client = mturk_client()

    print('Retrieving reviewable HITs...')
    pages = all_pages(
        client.list_reviewable_hits,
        Status='Reviewable',
        MaxResults=100
    )

    hits = []
    for page in pages:
        hits += page['HITs']

    for hit in hits:
        hit = client.get_hit(HITId=hit['HITId'])['HIT']
        already_done = hit['HITId'] in credited_hits

        if hit['Title'] == HIT_TITLE and not already_done:
            print('Collecting workers for HIT {}, title: `{}`'
                  .format(hit['HITId'], hit['Title']))

            credited_workers, credited_assignments = credit_hit(
                hit['HITId'], credited_workers, credited_assignments)

            #  assignments = client.list_assignments_for_hit(
            #      HITId=hit['HITId'],
            #      MaxResults=100,
            #      AssignmentStatuses=['Submitted']
            #  )
            #
            #  for ass in assignments['Assignments']:
            #      ass_id = ass['AssignmentId']
            #      worker_id = ass['WorkerId']
            #      print('\tCrediting worker {} on assignment {}'
            #            .format(worker_id, ass_id))
            #
            #      _ = client.approve_assignment(
            #          AssignmentId=ass_id,
            #          RequesterFeedback='Thank you for completing our experiment!',
            #          OverrideRejection=False
            #      )
            #      credited_workers.add(worker_id)
            #      credited_assignments.add(ass_id)

            credited_hits.add(hit['HITId'])

            np.savez(
                'credited.npz',
                credited_hits=np.array(list(credited_hits)),
                credited_workers=np.array(list(credited_workers)),
                credited_assignments=np.array(list(credited_assignments)),
            )
