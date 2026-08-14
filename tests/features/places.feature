Feature: Where it offers to look

  The first screen asks one question, so the answers on it have to be ones this
  machine can actually give. A folder that isn't there is a dead button, and the
  whole disk is a forty-second scan with a permission dialog in the middle — a
  fine thing to ask for on purpose, a bad thing to put under the cursor first.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: Every place offered is one this machine has
    When the browser asks where it can look
    Then every place it is offered is really there
    And it is offered somewhere to start

  Scenario: The whole disk is not one of them
    When the browser asks where it can look
    Then none of them is the whole disk

  Scenario: A folder this machine does not have is not offered
    Given "Documents" has been taken away
    When the browser asks where it can look
    Then "Documents" is not among them
    And it is offered somewhere to start
