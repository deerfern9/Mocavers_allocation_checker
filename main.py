import os
from loguru import logger
from Account import Account
from config import PROXY_TXT, PRIVATES_TXT, RESULTS_TXT, threads_count
from concurrent.futures import ThreadPoolExecutor, as_completed


def process_account(data):
    private, proxy = data
    account = Account(private, proxy)
    response = account.session.get('https://api.moca-id.mocaverse.xyz/api/sales-code/sales-result').json()
    bid_amount = response['bidAmount']
    purchases = response['purchases']
    nft = purchases['nftLots']
    gtd = purchases['publicLots']
    wl = purchases['waitlistLots']
    whales = purchases['whales']
    additional = purchases['additional']
    bonus = purchases['bonus']
    total_token_allocation = response['tokenAllocations']['total']
    return (f'{account.wallet_address}\t{nft}\t{gtd}\t{wl}\t{whales}\t{additional}\t{bonus}\t{bid_amount}\t'
            f'{total_token_allocation}\n')


def main():
    if 'data' not in os.listdir():
        os.mkdir('data')
        open('data/privates.txt', 'a').write('')
        open('data/proxies.txt', 'a').write('')
        logger.success('The directory and files were successfully created. Press Enter to exit')
        input()
        exit()

    privates = [line.strip() for line in open(PRIVATES_TXT).readlines()]
    proxies = [line.strip() for line in open(PROXY_TXT).readlines()]
    data_zip = list(zip(privates, proxies))

    with ThreadPoolExecutor(max_workers=threads_count) as executor:
        futures = [executor.submit(process_account, data) for data in data_zip]

        with open(RESULTS_TXT, 'w') as f:
            f.write(f'Address\tNFT lots\tGTD lots\tWL lots\tWhales\tAdditional\tBonus\tBid amount\t'
                    f'Token allocation\n')

            for future in as_completed(futures):
                result = future.result()
                f.write(result)
                print(result.replace('\t', ';').strip())


if __name__ == '__main__':
    main()