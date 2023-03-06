import json
import os
import sys

import requests
from dotenv import load_dotenv
load_dotenv(os.getcwd() + '\\settings.env')

API_KEY = os.environ.get('API_KEY')
CHECK_IP = os.environ.get('CHECK_IP')
TARGETS = os.environ.get('TARGETS').split(', ')

handled_error_codes = [400, 401, 404]

default_url = 'https://api.hosting.ionos.com/dns/v1/zones'
default_headers = {
    'accept': 'application/json',
    'X-API-Key': API_KEY
}


def get_public_ipv4():
    response = requests.get('https://ipv4.jsonip.com')
    return response


def get_public_ipv6():
    response = requests.get('https://ipv6.jsonip.com')
    return response


# works for all get requests
def simple_get(url, headers):
    response = requests.get(url, headers=headers)
    return response


def iterate_through_zones(zones):
    for zone in zones:
        zone_id = zone['id']
        zone_url = default_url + "/" + zone_id
        single_zone_response = simple_get(zone_url, default_headers)

        # further action with one zone
        if single_zone_response.status_code == 200:
            iterate_through_records(zone_url, single_zone_response)

        # client errors
        elif single_zone_response.status_code in handled_error_codes:
            pretty_print(single_zone_response)

        # server errors
        else:
            fatal_error(single_zone_response)


def iterate_through_records(zone_url, zone):
    for record in zone.json()['records']:
        if record['name'] in TARGETS:
            if (CHECK_IP == 'both' or CHECK_IP == 'ipv4') and record['type'] == 'A':
                record_handler(zone_url, record, public_ipv4)
            if (CHECK_IP == 'both' or CHECK_IP == 'ipv6') and record['type'] == 'AAAA':
                record_handler(zone_url, record, public_ipv6)


def record_handler(zone_url, record, ipaddress):
    record_id = record['id']
    if ipaddress['ip'] != record['content']:
        record_url = zone_url + '/records/' + record_id
        new_data = {'content': ipaddress['ip']}
        record_response = update_record_request(record_url, default_headers, new_data)

        if record_response.status_code == 200:
            print(f"Everything went good for \"{record['name']}\" and content is updated to {ipaddress['ip']}.")

        # client errors
        elif record_response.status_code in handled_error_codes:
            print(f"Something with \"{record['name']}\" went wrong.")
            pretty_print(record_response)

        # server errors
        else:
            fatal_error(record_response)


def update_record_request(url, headers, data):
    headers.update({'Content-Type': 'application/json'})
    response = requests.put(url, headers=headers, json=data)
    return response


def pretty_print(dictionary):
    print(json.dumps(dictionary.json(), indent=4))


def fatal_error(response):
    print("Something went terribly wrong.")
    if response.status_code == 500:
        pretty_print(response)


if __name__ == '__main__':

    public_ipv4 = None
    public_ipv6 = None
    failed_requests = 0

    if CHECK_IP == 'ipv4' or CHECK_IP == 'both':
        try:
            public_ipv4 = get_public_ipv4().json()
        except requests.exceptions.ConnectionError as e:
            print("Couldn't establish a connection to http://ipv4.jsonip.com")
            print(e)
            failed_requests += 1

    if CHECK_IP == 'ipv6' or CHECK_IP == 'both':
        try:
            public_ipv6 = get_public_ipv6().json()
        except requests.exceptions.ConnectionError as e:
            print("Couldn't establish a connection to http://ipv6.jsonip.com")
            print(e)
            failed_requests += 1

    # stops skript if there is no ip-address found
    if (CHECK_IP == 'both' and failed_requests == 2) or failed_requests == 1:
        sys.exit("No ip-address was found. No further action.")

    zones_response = simple_get(default_url, default_headers)

    # further action with all zones
    if zones_response.status_code == 200:
        iterate_through_zones(zones_response.json())

    # client errors
    elif zones_response.status_code in handled_error_codes:
        pretty_print(zones_response)

    # server errors
    else:
        fatal_error(zones_response)
