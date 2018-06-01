#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter

import boto3

DESCRIPTION = """
Print a list of the worker IDs associated with a given HIT or HIT set. If the
`--worker` flag is passed, searches for the passed worker ID within the list
of assignments.

Usage
-----
    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> get_workers_for_hit.py --hit <HIT ID / HIT Set Id> --worker <>
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


def mturk_client(print_msg=False, key_id=None, key=None):
    if print_msg:
        print("Connecting to mechanical turk...")

    if not key_id:
        key_id = os.environ['AWS_ACCESS_KEY_ID']

    if not key:
        key = os.environ['AWS_SECRET_ACCESS_KEY']

    client = boto3.client(
        'mturk',
        aws_access_key_id=key_id,
        aws_secret_access_key=key
    )
    return client


def get_workers_for_hit(hit_id=None, hit_group=None, worker=None, print_msg=False):
    client = mturk_client(print_msg)

    # get all HITS for the current account
    if print_msg:
        print('Retrieving HITs...')

    pages = all_pages(
        client.list_hits,
        MaxResults=100
    )

    if hit_id:
        key = 'HITId'
        value = args.hit
    elif hit_group:
        key = 'HITGroupId'
        value = args.hit_group

    for page in pages:
        result = [r for r in page['HITs'] if r[key] == value]

        if len(result):
            break

    if not len(result):
        print('Could not find a HIT with {} `{}`'.format(key, value))
        return

    asgn_tuples = []
    for hit in result:
        hit_id = hit['HITId']
        assignments = client.list_assignments_for_hit(HITId=hit_id)

        if print_msg:
            print('Searching Worker IDs for HIT ID `{}`'.format(hit_id))

        for assignment in assignments['Assignments']:
            workerId = assignment['WorkerId']
            status = assignment['AssignmentStatus']
            submit = assignment['SubmitTime'].strftime('%D %I:%M:%S %p')

            asgn_tuple = [hit_id, workerId, status, submit]
            asgn_tuples.append(asgn_tuple)

            if worker:
                if workerId == worker:
                    if print_msg:
                        print('\t{}\t{}\t{}'.format(workerId, status, submit))
                    return asgn_tuple
            else:
                if print_msg:
                    print('\t{}\t{}\t{}'.format(workerId, status, submit))

    # if worker wasn't found
    if worker:
        return None

    # else return the full list of worker IDs and statuses
    return asgn_tuples


if __name__ == "__main__":
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter)

    parser.add_argument(
        "--hit",
        metavar="ID",
        type=str,
        help="the HIT ID")

    parser.add_argument(
        "--hit_group",
        type=str,
        metavar="SET_ID",
        help="the HIT set/group ID")

    parser.add_argument(
        "--worker",
        metavar="ID",
        type=str,
        help="worker ID to look for")

    args = parser.parse_args()

    if not args.hit and not args.hit_group:
        print('Error: You must specify either --hit or --hit_group')
        sys.exit()

    if args.hit and args.hit_group:
        print('Error: --hit and --hit_group cannot both be set')
        sys.exit()

    _ = get_workers_for_hit(
        hit_id=args.hit,
        hit_group=args.hit_group,
        worker=args.worker,
        print_msg=True
    )
