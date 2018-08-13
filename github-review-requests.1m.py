#!/usr/bin/env python
# -*- coding: utf-8 -*-

# <bitbar.title>Github review requests</bitbar.title>
# <bitbar.desc>Shows a list of PRs that need to be reviewed</bitbar.desc>
# <bitbar.version>v0.1</bitbar.version>
# <bitbar.author>Adam Bogdał</bitbar.author>
# <bitbar.author.github>bogdal</bitbar.author.github>
# <bitbar.image>https://github-bogdal.s3.amazonaws.com/bitbar-plugins/review-requests.png</bitbar.image>
# <bitbar.dependencies>python</bitbar.dependencies>

import datetime
import json
import os
import sys
import ConfigParser

try:
    # For Python 3.x
    from urllib.request import Request, urlopen
except ImportError:
    # For Python 2.x
    from urllib2 import Request, urlopen

# Will look for all your config in ~/.bitbarrc
CONFIG_FILE = os.path.join(os.environ['HOME'], '.bitbarrc')
# You can replace this if you want to share config with other plugin (e.g. github_ci)
CONFIG_SECTION = 'github-review-requests'

# Keys to read:
# access_token=0123456789abcdef
# username=whoami
# hostname=github.skyscannertools.net
# filters=label:whatever

# (optional) PRs with this label (e.g 'in progress') will be grayed out on the list
WIP_LABEL = 'WIP'

QUERY = '''{
  search(query: "%(search_query)s", type: ISSUE, first: 100) {
    issueCount
    edges {
      node {
        ... on PullRequest {
          repository {
            nameWithOwner
          }
          author {
            login
          }
          createdAt
          number
          url
          title
          labels(first:100) {
            nodes {
              name
            }
          }
        }
      }
    }
  }
}'''


COLOURS = {
    'inactive': '#b4b4b4',
    'title': '#000000',
    'subtitle': '#586069'
}


class GithubReviewRequests:
    def __init__(self, api, token):
        self.api = api
        self.token = token

    def execute_query(self, query):
        headers = {
            'Authorization': 'bearer %s' % (self.token),
            'Content-Type': 'application/json'
        }
        data = json.dumps({'query': query}).encode('utf-8')
        req = Request(self.api, data=data, headers=headers)
        body = urlopen(req).read()
        return json.loads(body)

    def search_pull_requests(self, login, filters=''):
        search_query = 'type:pr state:open review-requested:%(login)s %(filters)s' % {'login': login, 'filters': filters}
        response = self.execute_query(QUERY % {'search_query': search_query})
        return response['data']['search']


def parse_date(text):
    date_obj = datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')
    return date_obj.strftime('%B %d, %Y')


def print_line(text, **kwargs):
    params = ' '.join(['%s=%s' % (key, value) for key, value in kwargs.items()])
    print('%s | %s' % (text, params) if kwargs.items() else text)


if __name__ == '__main__':
    if not os.path.isfile(CONFIG_FILE):
        print_line('Can\'t find ~/.bitbarrc')
        sys.exit(0)
    config = ConfigParser.RawConfigParser()
    config.read(CONFIG_FILE)
    host = config.get(CONFIG_SECTION, 'hostname')
    access_token = config.get(CONFIG_SECTION, 'access_token')
    username = config.get(CONFIG_SECTION, 'username')
    filters = config.get(CONFIG_SECTION, 'filters')

    if not all([access_token, username]):
        print_line('⚠ Github review requests', color='red')
        print_line('---')
        print_line('access_token and username cannot be empty')
        sys.exit(0)

    api = '''https://%s/api/graphql''' % (host)
    plugin = GithubReviewRequests(api, access_token)

    response = plugin.search_pull_requests(username, filters)

    print_line('#%s' % response['issueCount'])
    print_line('---')

    for pr in [r['node'] for r in response['edges']]:
        labels = [l['name'] for l in pr['labels']['nodes']]
        title = '%s - %s' % (pr['repository']['nameWithOwner'], pr['title'])
        title_color = COLOURS.get('inactive' if WIP_LABEL in labels else 'title')
        subtitle = '#%s opened on %s by @%s' % (pr['number'], parse_date(pr['createdAt']), pr['author']['login'])
        subtitle_color = COLOURS.get('inactive' if WIP_LABEL in labels else 'subtitle')

        print_line(title, size=16, color=title_color, href=pr['url'])
        print_line(subtitle, size=12, color=subtitle_color)
        print_line('---')
