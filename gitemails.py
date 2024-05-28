import requests
import time
import csv
import argparse
from datetime import datetime
import warnings

# Suppress the insecure request warnings (requests verify=False)
# Used for testing self-hosted git labs that could be self-signed
warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

def token_generator(token_list):
    while True:
        for token in token_list:
            yield token

def load_tokens_from_file(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines() if line.strip()]

def get_api_response(url, token_gen=None):
    while True:
        headers = {'User-Agent': 'Mozilla/5.0'}
        if token_gen:
            token = next(token_gen)  # Get the next token
            headers['Authorization'] = f'token {token}'

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            return response
        elif response.status_code == 403 and 'X-RateLimit-Reset' in response.headers and response.headers['X-RateLimit-Remaining'] == '0':
            print("\nRate limit exceeded!!!")
            if token_gen:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} Rate limit exceeded. Switching token and retrying after 60 seconds.")
                print("\nRetrying in 60 seconds.")
                time.sleep(60)
                continue
            else:
                print("\nIt is highly recommended to use GitHub tokens if you are scanning large targets")
                print("     Tokens can be generated at https://github.com/settings/tokens\n")
                print("\nRetrying in 60 seconds.")
                time.sleep(60)
                continue
        else:
            response.raise_for_status()

def get_repositories_for_user(username, token_gen=None):
    url = f"https://api.github.com/users/{username}/repos"
    repos = []
    print(f'Searching for repos for {username}')
    while url:
        response = get_api_response(url, token_gen)
        repositories = response.json()

        for repo in repositories:
            repo_data = {
                'name': repo['name'],
                'url': repo['html_url'],
                'description': repo.get('description'),
                'owner': username
            }
            repos.append(repo_data)
            print(f'    Found repo: {repo["name"]}')

        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            break

    return repos

def get_repositories_for_org(orgname, token_gen=None):
    url = f"https://api.github.com/orgs/{orgname}/repos"
    repos = []
    print(f'Searching for repos for organization {orgname}')
    while url:
        response = get_api_response(url, token_gen)
        repositories = response.json()

        for repo in repositories:
            repo_data = {
                'name': repo['name'],
                'url': repo['html_url'],
                'description': repo.get('description'),
                'owner': orgname
            }
            repos.append(repo_data)
            print(f'    Found repo: {repo["name"]}')

        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            break
            
    return repos

def get_emails_from_github_commits(repo, csv_writer, token_gen=None):
    url = f"https://api.github.com/repos/{repo['owner']}/{repo['name']}/commits"
    repo_emails = set()
    commit_usernames = []

    while url:
        print(f'Searching Project Commits ({repo["name"]}): {url}')
        response = get_api_response(url, token_gen)
        commits = response.json()

        for commit in commits:
            try:
                author_email = commit['commit']['author']['email']
                author_name = commit['commit']['author']['name']
                try:
                    author_gh_username = commit['author']['login']
                    commit_usernames.append(author_gh_username)
                except:
                    author_gh_username = 'Not Found'
                committer_email = commit['commit']['committer']['email']
                committer_username = commit['commit']['committer']['name']
                email_author_pair = (author_gh_username, author_email, author_name)
                email_committer_pair = (committer_username, committer_email, committer_username)
                commit_url = commit['html_url']
                commit_api = url

                if 'noreply' not in author_email and email_author_pair not in repo_emails:
                    repo_emails.add(email_author_pair)
                    role = "Owner" if author_gh_username.lower() == repo['owner'].lower() else "Contributor"
                    csv_writer.writerow([repo['name'], repo['url'], repo['owner'], author_gh_username, author_name, role, 'Commit Author', author_email, commit_url, commit_api])
                    unique_combos.add(email_author_pair)
                    print(f"    Author email logged - {author_email}")
                
                if 'noreply' not in committer_email and email_committer_pair not in repo_emails:
                    repo_emails.add(email_committer_pair)
                    role = "Owner" if committer_username.lower() == repo['owner'].lower() else "Contributor"
                    csv_writer.writerow([repo['name'], repo['url'], repo['owner'], committer_username, committer_username, role, 'Commit Committer', committer_email, commit_url, commit_api])
                    unique_combos.add(email_committer_pair)
                    print(f"    Committer email logged - {committer_email}")

            except Exception as e:
                print(url)
                print(commit)
                print("Error processing commit:", e)

        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            break

    return commit_usernames

def recursive_search(usernames, depth, token_gen, csv_writer, current_depth=0):
    if current_depth > depth:
        return

    new_usernames = set()
    total_users = len(usernames)
    
    for i, username in enumerate(usernames):
        print(f"Fetching repositories for user: {username} ({i+1}/{total_users})")
        repositories = get_repositories_for_user(username, token_gen)
        for repo in repositories:
            commit_usernames = get_emails_from_github_commits(repo, csv_writer, token_gen)
            new_usernames.update(commit_usernames)

    recursive_search(new_usernames, depth, token_gen, csv_writer, current_depth + 1)

def main():
    parser = argparse.ArgumentParser(
        description='This script fetches GitHub repositories and commit emails for a specified user or organization.\nGitHub: zcrosman :)',
        epilog='''Example usage:
    python gitemails.py --user john_doe 
    python gitemails.py --user john_doe --token YOUR_GITHUB_TOKEN
    python gitemails.py --org acme_corp --token-file path/to/tokens_file.txt
    ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group_user_org = parser.add_mutually_exclusive_group(required=True)
    group_token = parser.add_mutually_exclusive_group(required=False)

    group_user_org.add_argument('--user', type=str, help='GitHub username to fetch repositories for')
    group_user_org.add_argument('--org', type=str, help='GitHub organization to fetch repositories for')
    group_token.add_argument('--token', type=str, help='GitHub token')
    group_token.add_argument('--token-file', type=str, help='File containing GitHub token(s)')
    parser.add_argument('--depth', type=int, default=0, help='Depth for recursive search of commit usernames')

    args = parser.parse_args()

    tokens = []
    if args.token_file:
        tokens = load_tokens_from_file(args.token_file)
    elif args.token:
        tokens = [args.token]

    token_gen = None
    if tokens:
        token_gen = token_generator(tokens)
    
    repositories = []
    initial_usernames = []
    global unique_combos
    unique_combos = set()

    if args.user:
        print(f"Fetching repositories for user: {args.user}")
        repositories = get_repositories_for_user(args.user, token_gen)
        initial_usernames.append(args.user)
    elif args.org:
        print(f"Fetching repositories for organization: {args.org}")
        repositories = get_repositories_for_org(args.org, token_gen)
        org_users = set()
        with open(f'github-data-{args.org}.csv', 'a', newline='', encoding='utf-8') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(['Repo Name', 'Repo URL', 'Repo Owner', 'GH Username', 'Name', 'Role', 'Type', 'Email', 'Commit URL', 'Commit API URL'])
            for repo in repositories:
                commit_usernames = get_emails_from_github_commits(repo, csv_writer, token_gen)
                org_users.update(commit_usernames)
        initial_usernames = list(org_users)

    filename = f'github-data-{args.user or args.org}.csv'
    commit_usernames = []
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(['Repo Name', 'Repo URL', 'Repo Owner', 'GH Username', 'Name', 'Role', 'Type', 'Email', 'Commit URL', 'Commit API URL'])
        for repo in repositories:
            commit_usernames.extend(get_emails_from_github_commits(repo, csv_writer, token_gen))

        unique_usernames = list(set(commit_usernames))
        print("\nUnique commit usernames:")
        for username in unique_usernames:
            print(username)

        if args.depth > 0:
            recursive_search(initial_usernames, args.depth, token_gen, csv_writer)

    # Write unique combinations to a separate CSV file
    unique_combos_filename = f'unique-combos-{args.user or args.org}.csv'
    with open(unique_combos_filename, 'w', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(['GH Username', 'Email', 'Name'])
        for combo in unique_combos:
            csv_writer.writerow(combo)

if __name__ == "__main__":
    main()
