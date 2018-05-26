#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter

import boto3

DESCRIPTION = \
    """
Return the list of worker IDs that submitted for a given HIT.

Usage
-----
    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> get_workers_for_hit.py <HIT ID / HIT Set Id>
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


if __name__ == "__main__":
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter)

    parser.add_argument(
        "--hit_group",
        type=str,
        metavar="SET_ID",
        help="the HIT set/group ID")

    parser.add_argument(
        "--hit_id",
        metavar="ID",
        type=str,
        help="the HIT ID")

    parser.add_argument(
        "--worker",
        metavar="WORKER_ID",
        type=str,
        help="worker ID to search for")

    args = parser.parse_args()

    if not args.hit_id and not args.hit_group:
        print('Error: You must specify either --hit_id or --hit_group')
        sys.exit()

    if args.hit_id and args.hit_group:
        print('Error: --hit_id and --hit_group cannot both be set')
        sys.exit()


    client = mturk_client()

    # get all HITS for the current account
    print('Retrieving HITs...')
    pages = all_pages(
        client.list_hits,
        MaxResults=100
    )

    if args.hit_id:
        key = 'HITId'
        value = args.hit_id
    elif args.hit_group:
        key = 'HITGroupId'
        value = args.hit_group

    for page in pages:
        result = [r for r in page['HITs'] if r[key] == value]

        if len(result):
            break

    if not len(result):
        print('Could not find a HIT with {} `{}`'.format(key, value))
        sys.exit()

    for hit in result:
        hit_id = hit['HITId']
        assignments = client.list_assignments_for_hit(HITId=hit_id)

        print('Searching Worker IDs for HIT ID `{}`'.format(hit_id))
        for assignment in assignments['Assignments']:
            workerId = assignment['WorkerId']
            status = assignment['AssignmentStatus']
            submit = assignment['SubmitTime'].strftime('%D %I:%M:%S %p')
            if args.worker:
                if workerId == args.worker:
                    print('\t{}\t{}\t{}'.format(workerId, status, submit))
                    sys.exit()
            else:
                print('\t{}\t{}\t{}'.format(workerId, status, submit))
