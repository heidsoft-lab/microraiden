import requests
from eth_utils import encode_hex
from munch import Munch

from raiden_mps.header import HTTPHeaders
from .client import Client


class HTTPClient(object):
    def __init__(self, client: Client, api_endpoint, api_port):
        self.client = client
        self.api_endpoint = api_endpoint
        self.api_port = api_port

        self.channel = None
        self.requested_resource = None
        self.retry = False

    def run(self, requested_resource=None):
        if requested_resource:
            self.requested_resource = requested_resource
        self.on_init()
        resource = None
        self.retry = True
        while self.retry and self.requested_resource:
            self.retry = False
            resource = self._request_resource()

        self.on_exit()
        return resource

    def _request_resource(self):
        """
        Performs a simple GET request to the HTTP server with headers representing the given
        channel state.
        """
        headers = Munch()
        headers.contract_address = self.client.channel_manager_address
        if self.channel:
            headers.balance = str(self.channel.balance)
            headers.balance_signature = encode_hex(self.channel.balance_sig)
            headers.sender_address = self.channel.sender
            headers.receiver_address = self.channel.receiver
            headers.open_block = str(self.channel.block)

        url = 'http://{}:{}/{}'.format(self.api_endpoint, self.api_port, self.requested_resource)
        response = requests.get(url, headers=HTTPHeaders.serialize(headers))
        headers = HTTPHeaders.deserialize(response.headers)

        if response.status_code == requests.codes.OK:
            self.on_success(response.content, headers.get('cost'))
            return response.content
        elif response.status_code == requests.codes.PAYMENT_REQUIRED:
            if 'insuf_confs' in headers:
                self.on_insufficient_confirmations(headers.insuf_confs)
            elif 'insuf_funds' in headers:
                self.on_insufficient_funds()
            else:
                self.on_payment_requested(
                    headers.receiver_address, int(headers.price), headers.get('contract_address')
                )

    def on_init(self):
        pass

    def on_exit(self):
        pass

    def on_success(self, resource, cost: int):
        pass

    def on_payment_requested(self, receiver: str, price: int, channel_manager_address: str):
        pass

    def on_insufficient_funds(self):
        pass

    def on_insufficient_confirmations(self, pending_confirmations: int):
        pass
