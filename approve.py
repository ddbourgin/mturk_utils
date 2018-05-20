#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import boto3
import numpy as np

"""
Batch HIT approver for psiturk. Only approves HITS that are listed as reviewable,
saving a log of subject and HIT IDs that it approves (to guard against double
payments, etc.) Script can be run multiple times as more HITs are posted.

Usage
-----
Place in the same directory as the experiment's `config.txt`, or pass the title of
the HIT as a positional argument at the command line

    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> approve.py <HIT title>
"""

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


if __name__ == "__main__":
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "title",
        metavar="TITLE",
        type=str,
        nargs='?',
        default='',
        help="The title of the experiment/HIT.")

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

    # try loading the set of already-credited HIT IDs from a previous run
    already_credited = set()
    if os.path.lexists('credited_hits.npy'):
        already_credited = set(np.load('credited_hits.npy'))

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
        already_done = hit['HITId'] in already_credited

        if hit['Title'] == HIT_TITLE and not already_done:
            print('Collecting workers for HIT {}, title: `{}`'
                  .format(hit['HITId'], hit['Title']))

            assignments = client.list_assignments_for_hit(
                HITId=hit['HITId'],
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
                already_credited.add(hit['HITId'])

            np.save('credited_hits', np.array(list(already_credited)))
