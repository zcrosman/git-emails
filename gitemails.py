import requests
import time
import csv
import argparse

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

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response
        elif response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers and response.headers['X-RateLimit-Remaining'] == '0':
            if token_gen:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} Rate limit exceeded. Switching token and retrying after {retry_after} seconds.")
                time.sleep(retry_after)
                continue
            else:
                print("Rate limit exceeded and no additional tokens available.")
                break
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

    while url:
        print(f'Searching Project Commits ({repo["name"]}): {url}')
        response = get_api_response(url, token_gen)
        commits = response.json()

        for commit in commits:
            try:
                author_email = commit['commit']['author']['email']
                author_username = commit['commit']['author']['name']
                committer_email = commit['commit']['committer']['email']
                committer_username = commit['commit']['committer']['name']
                email_author_pair = (author_email, author_username)
                email_commiter_pair = (committer_email, committer_username)
                commit_url = commit['html_url']
                commit_api = url

                if 'noreply' not in author_email and email_author_pair not in repo_emails:
                    repo_emails.add(email_author_pair)
                    role = "Owner" if author_username.lower() == repo['owner'].lower() else "Contributor"
                    csv_writer.writerow([repo['name'], repo['url'], repo['owner'], author_username, role, 'Commit Author', author_email, commit_url, commit_api])
                    print(f"    author email logged - {author_email}")
                if 'noreply' not in committer_email and email_commiter_pair not in repo_emails:
                    repo_emails.add(email_commiter_pair)
                    role = "Owner" if committer_username.lower() == repo['owner'].lower() else "Contributor"
                    csv_writer.writerow([repo['name'], repo['url'], repo['owner'], committer_username, role, 'Commit Committer', committer_email, commit_url, commit_api])
                    print(f"    committer email logged - {committer_email}")

            except Exception as e:
                print("Error processing commit:", e)

        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            break

def main():
    parser = argparse.ArgumentParser(
        description='This script fetches GitHub repositories and commit emails for a specified user or organization.\nGithub:zcrosman :)',
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
    if args.user:
        print(f"Fetching repositories for user: {args.user}")
        repositories = get_repositories_for_user(args.user, token_gen)
    elif args.org:
        print(f"Fetching repositories for organization: {args.org}")
        repositories = get_repositories_for_org(args.org, token_gen)

    filename = f'github-data-{args.user or args.org}.csv'
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(['Repo Name', 'Repo URL', 'Repo Owner', 'Username', 'Role', 'Type', 'Email', 'Commit URL', 'Commit API URL'])
        for repo in repositories:
            get_emails_from_github_commits(repo, csv_writer, token_gen)

if __name__ == "__main__":
    main()
