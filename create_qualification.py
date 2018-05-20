#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import boto3
import numpy as np

"""
Create a new worker qualification. Useful in preparation for making
invitation-only makeup HITs.

Usage
-----
    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> create_qualification.py <Qualification Name> <Long Description>
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
        "name",
        metavar="NAME",
        type=str,
        nargs=1,
        help="The name for the new qualification. This name is used to "
        "represent the qualification to workers, and to find the type using a "
        "qualification type search.")

    parser.add_argument(
        "description",
        metavar="DESCRIPTION",
        type=str,
        nargs=1,
        help="A long description for the Qualification type. The long "
        "description is displayed when a worker examines the qualification.")

    args = parser.parse_args()

    client = mturk_client()

    response = client.create_qualification_type(
        Name=args.name,
        Description=args.description,
        QualificationTypeStatus='Active',
        RetryDelayInSeconds=123,
        AutoGranted=True,
        AutoGrantedValue=1
    )

    try:
        response = response['QualificationType']
    except KeyError:
        raise Exception('Error creating qualification:\n{}'.format(response))

    print("Created qualification!")
    print("\tName: {}".format(response['Name']))
    print("\tID: {}".format(response['QualificationTypeId']))
    print("\tDescription: {}".format(response['Description']))
    print("\tIs Requestable: {}".format(response['IsRequestable']))
