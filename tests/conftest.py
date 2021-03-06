import json
import pytest
import requests

from kin_base.asset import Asset
from kin_base.keypair import Keypair
from kin_base.builder import Builder

import logging
logging.basicConfig()

#logging.getLogger().setLevel(logging.DEBUG)


def pytest_addoption(parser):
    parser.addoption(
        "--testnet",
        action="store_true",
        default=False,
        help="whether testing on testnet instead of local")


@pytest.fixture(scope='session')
def testnet(request):
    return request.config.getoption("--testnet")


@pytest.fixture(scope='session')
def setup():
    class Struct:
        """Handy variable holder"""

        def __init__(self, **entries):
            self.__dict__.update(entries)

    issuer_keypair = Keypair.random()
    test_asset = Asset('TEST', issuer_keypair.address().decode())

    # local testnet (kinecosystem docker)
    from kin_base.network import NETWORKS
    # we will leave this passphrase instead of changing every envelop in the test suite
    NETWORKS['CUSTOM'] = 'Integration Test Network ; zulucrypto'
    return Struct(
        type='local',
        network='CUSTOM',
        issuer_keypair=issuer_keypair,
        test_asset=test_asset,
        horizon_endpoint_uri='http://localhost:8008',
        friendbot_url='http://localhost:8001')


class Helpers:
    """A container for helper functions available to all tests"""

    @staticmethod
    def fund_account(setup, address):
        for attempt in range(3):
            try:
                r = requests.get(setup.friendbot_url +
                                 '?addr=' + address)
                j = json.loads(r.text)
                if 'hash' in j:
                    print('\naccount {} funded successfully'.format(address))
                    return
                elif 'op_already_exists' in j:
                    print('\naccount {} already exists, not funded'.format(
                        address))
                    return
                else:
                    raise Exception('unexpected friendbot reply')
            except Exception as e:
                print('\naccount {} funding error: {} {}'.format(
                    address, r.status_code, r.text))
        raise Exception('account {} funding failed'.format(address))

    @staticmethod
    def trust_asset(setup, secret_key, memo_text=None):
        """A helper to establish a trustline"""
        builder = Builder(
            secret=secret_key,
            horizon_uri=setup.horizon_endpoint_uri,
            network=setup.network)
        builder.append_trust_op(setup.test_asset.issuer, setup.test_asset.code)
        if memo_text:
            builder.add_text_memo(memo_text[:28])  # max memo length is 28
        builder.sign()
        reply = builder.submit()
        return reply.get('hash')

    @classmethod
    def fund_asset(cls, setup, address, amount, memo_text=None):
        """A helper to fund account with test asset"""
        return cls.send_asset(setup, setup.issuer_keypair.seed(), address,
                              amount, memo_text)

    @classmethod
    def send_asset(cls, setup, secret_key, address, amount, memo_text=None):
        """A helper to send asset"""
        builder = Builder(
            secret=secret_key,
            horizon_uri=setup.horizon_endpoint_uri,
            network=setup.network)
        builder.append_payment_op(address, amount, setup.test_asset.code,
                                  setup.test_asset.issuer)
        if memo_text:
            builder.add_text_memo(memo_text[:28])  # max memo length is 28
        builder.sign()
        reply = builder.submit()
        return reply.get('hash')


@pytest.fixture(scope='session')
def helpers():
    return Helpers
