import json
from datetime import datetime
from json import JSONDecodeError
from typing import Iterator

import requests


class Fuse5APIException(Exception):
    pass


class Fuse5Client:
    def __init__(self, api_key: str, api_url: str, timeout: int = 30):
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout

    def export_to_csv(self, fields: list[str], changed_since: datetime = None) -> str:
        identifier = None

        if changed_since is not None:
            identifier = dict(changedsince=changed_since.strftime("%m-%d-%Y %H:%M:%S"))

        return self._request("product/export", params=fields, identifier=identifier, timeout=3600)['data']

    def get_locations(self) -> list[dict]:
        return self._request("location/all")['data']

    def create_sales_order(self, params: dict):
        return self._request("sales_order/create", params=params)['data']

    def search_sales_order_by_customer_order_id(self, account_number: str, customer_order_id: str) -> dict | None:
        if orders := self.get_sales_orders(account_number=account_number, customerpo=customer_order_id):
            return next((order for order in orders if order['customerpo'] == customer_order_id), None)

    def search_sales_order(self, keyword: str):
        return self._get_data("sales_order/search", identifier={'searchkeyword': keyword})

    def get_sales_order(self, sales_order_number: str):
        return self._get_data("sales_order/get", identifier={'sales_order_number': sales_order_number})

    def _get_data(self, api_endpoint: str, params: dict | list = None, identifier: dict = None) -> dict | None:
        try:
            return self._request(api_endpoint, params=params, identifier=identifier)['data']
        except Fuse5APIException as e:
            if 'E013' in str(e):
                # not found
                return None

    def get_sales_orders(self, *,
                         account_number: str = None,
                         sales_order_status: str = None,
                         sort_column: str = "sales_order_created_date",
                         sort_order: str = "desc",
                         search: str = None,
                         customerpo: str = None,
                         page_size: int = 100,
                         **kwargs
                         ) -> Iterator[dict]:

        identifier = {
            "limit": page_size,
            "offset": 0,
            "account_number": account_number,
            "sales_order_status": sales_order_status,
            "sort_column": sort_column,
            "sort_order": sort_order,
            "search": search,
            "customerpo": customerpo,
            **kwargs
        }

        return self._get_iterable("sales_order/history", identifier=identifier)

    def _get_iterable(self, api_endpoint: str, identifier: dict, params: dict | list = None, ) -> Iterator[dict]:
        assert 'offset' in identifier
        assert 'limit' in identifier

        total = identifier['offset'] + 1

        while identifier['offset'] < total:
            data = self._get_data(api_endpoint, params=params, identifier=identifier)

            if data is None:
                return None

            total = int(data['total'])
            for item in data['rows']:
                yield item

            identifier['offset'] += identifier["limit"]

    def _request(self,
                 api_endpoint: str,
                 params: dict | list = None,
                 identifier: dict = None,
                 method: str = 'POST',
                 timeout: int = None
                 ):
        timeout = timeout or self.timeout

        res = requests.request(
            method,
            self.api_url,
            data={'data': json.dumps(self._get_request_data(api_endpoint, params, identifier))},
            timeout=timeout
        )

        res.raise_for_status()

        try:
            res_data = res.json()['services'][0]['response']
        except (KeyError, IndexError, JSONDecodeError):
            raise Exception('Unexpected response from the Fuse 5 server', res.content)

        if not res_data['status']:
            # something went wrong
            messages = '\n'.join(str(item) for item in res_data['msg'])
            raise Fuse5APIException(messages, res.content)

        return res_data

    def _get_request_data(self,
                          api_endpoint: str,
                          params: dict | list = None,
                          identifier: dict = None
                          ) -> dict:

        extra_params = {}

        if params is not None:
            extra_params['params'] = params

        if identifier is not None:
            extra_params['identifier'] = identifier

        return {
            "authenticate": {
                "apikey": self.api_key
            },
            "services": [
                {
                    "call": api_endpoint,
                }
                | extra_params
            ]
        }
