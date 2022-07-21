# Script to find resources in AWS by an specific tag missing
# Example basic execution: python find_untagged_resources.py EMNF
# Example of more complex execution: python find_untagged_resources.py EMNF --keywords jenkins,monitor,feedback,certification
# Credits to https://medium.com/@CevoAustralia/using-the-new-resource-tagging-api-in-anger-1bfb2fe38242
# Taken some of its code and modified for the needs with a some (a lot) of modifications

import boto3
import sys
import csv
import argparse

client = boto3.client('resourcegroupstaggingapi')


def specific_lookup(keywords, resultset):
    keywords_subset = list()
    items_with_no_tags = list()

    for key in keywords.split(','):
        for r in resultset:
            # first search in the arn
            if key in r['ResourceARN']:
                keywords_subset.append(r)

            # search in the Tags
            next_result = next((item for item in r['Tags'] if item["Value"] == key), None)
            if next_result:
                keywords_subset.append(r)

    for r in resultset:
        if not r['Tags']:
            items_with_no_tags.append(r)


    print("Saving File with " + str(len(keywords_subset)) + " resources with keywords ...")
    save_file('resources_keywords.csv', keywords_subset)

    print("Saving File with " + str(len(items_with_no_tags)) + " resources with no tags at all ...")
    save_file('resources_notags.csv', items_with_no_tags)


def lookup(tag_value, keywords):
    
    def lookup_for_tags(token):
        response = client.get_resources(
            PaginationToken=token,
            ResourcesPerPage=50,
        )
        return response

    total_results = list()

    response = lookup_for_tags("")
    page_token = ""

    while True:
        total_results += response["ResourceTagMappingList"]

        page_token = response["PaginationToken"]
        if page_token == "":
            break
        response = lookup_for_tags(page_token)


    index = 0
    resultset = list()
    for result in total_results:
        next_result =  not next((item for item in result['Tags'] if item["Key"] == tag_value), None)
        if next_result:
                resultset.append(total_results[index])

        index += 1

    print("Total Resources found: " + str(len(total_results)))
    print("Total Resources found not tagged with "+ str(tag_value)+": " + str(len(resultset)))

    print("\nCount of Resources not tagged with ")
    for arn, value in add_by_arn(resultset).items():
        print(arn +": " + str(value))

    print("\nSaving File with all resources with tags ...")
    save_file('resources_all.csv', total_results)

    print("Saving File with "+ str(len(resultset)) +" resources not tagged with "+ str(tag_value) +" ...")
    save_file('resources_withnot_'+str(tag_value)+'.csv', resultset)

    add_by_arn(resultset)

    if keywords:
        specific_lookup(keywords, resultset)


def add_by_arn(resultset):
    types_count = dict()
    # initialize the dict with 0
    for r in resultset:
        arn = r['ResourceARN']
        arn = arn[15:] # remove the initial part that includes teh region and the arn
        arn = arn[0:arn.find(':')] # remove everything after the first :
        types_count[arn] = 0 # initialize it

    # start the counter
    for arn in types_count:
        for r in resultset:
            if arn in r['ResourceARN']:
                types_count[arn] += 1

    return types_count

def save_file(filename, resultset):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['arn', 'tags']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in resultset:
            writer.writerow({'arn': r['ResourceARN'], 'tags': r['Tags']})

def parse_args(args):
    parser = argparse.ArgumentParser(
        prog="tag_lookup",
        description="Search for resources based on one tag.",
    )
    parser.add_argument('tag_value', help="The value of the tag key to filter on")
    parser.add_argument('--keywords', default=None,
        help="Keywords separated by comma to look deeper")
    return parser.parse_args(args)

def main():
    cli_args = sys.argv[1:]
    args = parse_args(cli_args)
    lookup(args.tag_value, args.keywords)

if __name__ == '__main__':
    main()