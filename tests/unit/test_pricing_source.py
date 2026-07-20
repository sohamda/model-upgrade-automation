"""Unit tests for the Azure Retail Prices client."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.recommender.pricing_source import RetailPricesClient
from src.shared.errors import DependencyUnavailableError

_PAGE_ONE = {
    "Items": [
        {
            "meterId": "meter-a",
            "skuName": "gpt-4.1 Input Tokens",
            "unitPrice": 0.0025,
            "retailPrice": 0.0025,
        }
    ],
    "NextPageLink": "https://prices.azure.com/api/retail/prices?page=2",
}

_PAGE_TWO = {
    "Items": [
        {
            "meterId": "meter-b",
            "skuName": "gpt-4.1 Output Tokens",
            "retailPrice": 0.01,
        }
    ],
    "NextPageLink": None,
}


class RetailPricesClientTests(unittest.TestCase):
    def test_given_paginated_response_when_fetching_then_items_are_combined(self) -> None:
        # Arrange
        client = RetailPricesClient()

        # Act
        with patch.object(
            RetailPricesClient, "_fetch_json", side_effect=[_PAGE_ONE, _PAGE_TWO]
        ):
            prices = client.fetch_prices("eastus")

        # Assert
        self.assertEqual(len(prices), 2)
        self.assertEqual(prices[0]["meterId"], "meter-a")
        self.assertEqual(prices[1]["meterId"], "meter-b")

    def test_given_meter_id_when_matching_then_exact_price_is_returned(self) -> None:
        # Arrange
        client = RetailPricesClient()
        prices = _PAGE_ONE["Items"] + _PAGE_TWO["Items"]

        # Act
        price = client.unit_price_for("meter-b", None, prices)

        # Assert
        self.assertEqual(price, 0.01)

    def test_given_sku_name_when_matching_then_fuzzy_price_is_returned(self) -> None:
        # Arrange
        client = RetailPricesClient()
        prices = _PAGE_ONE["Items"] + _PAGE_TWO["Items"]

        # Act
        price = client.unit_price_for(None, "output tokens", prices)

        # Assert
        self.assertEqual(price, 0.01)

    def test_given_unmatched_meter_and_sku_when_matching_then_none_is_returned(self) -> None:
        # Arrange
        client = RetailPricesClient()
        prices = _PAGE_ONE["Items"] + _PAGE_TWO["Items"]

        # Act
        price = client.unit_price_for("missing", "nonexistent", prices)

        # Assert
        self.assertIsNone(price)

    def test_given_empty_response_when_fetching_then_dependency_error(self) -> None:
        # Arrange
        client = RetailPricesClient()

        # Act / Assert
        with patch.object(RetailPricesClient, "_fetch_json", return_value={}):
            with self.assertRaises(DependencyUnavailableError):
                client.fetch_prices("eastus")


if __name__ == "__main__":
    unittest.main()
