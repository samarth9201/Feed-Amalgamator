"""This interface provides an abstraction (ports/adapter model) to insulate internal code from external API changes.

Any module interacting with the Mastodon API post-oauth (for data collection) should do so strictly through this layer"""

import logging

import mastodon.errors
from mastodon import MastodonAPIError, Mastodon

from feed_amalgamator.helpers.custom_exceptions import (
    InvalidApiInputError,
    MastodonConnError,
)


class MastodonDataInterface:
    """Adapter Class for responsible for handling API calls for data processing AFTER Oauth.
    All calls to the API after oauth should go through this layer to insulate code from third party
    libraries.
    """

    def __init__(self, logger: logging.Logger):
        """We pass in a logger instead of creating a new one
        As we want logs to be logged to the program calling the interface
        rather than have separate logs for the interface layer specifically"""
        self.logger = logger
        """This is the client to perform actions on the user's behalf"""
        self.user_client = None
        """Hard coded required scopes for the app to work"""
        self.REQUIRED_SCOPES = ["read", "write", "push"]
        """The redirect URI required by the API to generate certain urls"""
        self.REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

    def start_user_api_client(self, user_domain: str, user_access_token: str):
        """
        Function to start a new client using the authorization code provided by the user.
        Does a sanity check to see if the user api access token is valid
        @param user_domain: User's account domain (eg. mstdn.social, tomorrow.io). Basically, which server
        the user's account is on
        @param user_access_token: The user access token generated from the auth procedure
        @return: None, but side effect of setting user_client
        """
        try:
            self.logger.info("Starting user api client")
            client = Mastodon(access_token=user_access_token, api_base_url=user_domain)
            # Getting 1 post from timeline to sanity check if the user access token was valid
            client.timeline(timeline="home", limit=1)
            self.user_client = client
            self.logger.info("Successfully started user API client")
        except mastodon.errors.MastodonUnauthorizedError:
            error_msg = (
                "start_user_api_client failed as the access token provided was invalid"
            )
            self.logger.error(error_msg)
            raise InvalidApiInputError(error_msg)
        except (ConnectionError, MastodonAPIError) as err:
            conn_error_msg = "Encountered error {e} in start_user_api_client".format(
                e=err
            )
            self.logger.error(conn_error_msg)
            raise MastodonConnError(conn_error_msg)

    # === Functions to get data from here on out =====
    def get_timeline_data(self, timeline_name: str, num_posts_to_get: int, num_tries=3):
        """
        @param timeline_name: Name of the timeline to get data from
        @param num_posts_to_get: Number of posts to obtain from the timeline
        @param num_tries: Number of tries to get the data before giving up
        @return:
        """
        assert self.user_client is not None, "User client has not been started"
        for i in range(num_tries):
            try:
                self.logger.info("Starting to get timeline data")
                timeline = self.user_client.timeline(
                    timeline=timeline_name, limit=num_posts_to_get
                )
                standardized_timeline = self._standardize_api_objects(timeline)
                self.logger.info("Successfully obtained timeline data")
                return standardized_timeline
            except (ConnectionError, MastodonAPIError) as err:
                self.logger.error(
                    "Encountered error {e} in start_user_api_client." "Retrying".format(
                        e=err
                    )
                )

        error_message = "Failed to get raw timeline data after trying {n} times. Throwing error".format(
            n=num_tries
        )
        self.logger.error(error_message)
        raise MastodonConnError(error_message)

    def _standardize_api_objects(
        self, raw_timeline: mastodon.utility.AttribAccessList
    ) -> list[dict]:
        """
        @param raw_timeline: Raw timeline object generated by the third party API of type mastodon.utility
        @return: Standardized dictionary of information contained in the API object
        """
        # Simple conversion for now, but will come in very handy if there is a breaking API change
        return [dict(item) for item in raw_timeline]