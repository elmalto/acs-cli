"""Tests for `service` subcommand."""

import pytest
import sys
import time

class TestDCOS():

    slow = pytest.mark.skipif(
        not pytest.config.getoption("--runslow"),
        reason="need --runslow option to run"
    )

    def test_deployment(self, service):
        response = str(service.marathonCommand('apps'))
        service.log.info("response from marathon command: " + response)
        assert '{\"apps\":[]}' in response

        with open ('marathon-app.json', "r") as marathonfile:
            data=marathonfile.read().replace('\n', '').replace("\"", "\\\"")
        response = service.marathonCommand('groups', 'POST', data)

        url = "http://" + service.getAgentEndpoint()

        for i in range (0,10):
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    break
            except:
                e = sys.exc_info()[0]
                time.sleep(5)

        assert i >= 9

        service.marathonCommand('groups/azure?force=true', 'DELETE')
        response = str(service.marathonCommand('apps'))
        assert '{"apps":[]}' in response
