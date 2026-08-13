Feature: What the browser can do

  The page needs three things the survey alone does not give it: somewhere to
  collect what you have chosen, a way to see the same file twice, and a way to
  analyse a folder the server never walked.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: The browser collects things and empties them in one go
    When the browser surveys the machine
    And the browser baskets "Sites/client-app/node_modules"
    And the browser empties the basket
    Then the response says what was freed
    And "Sites/client-app/node_modules" is gone from where it was
    And the browser can undo it

  Scenario: The browser is warned before it can bin something protected
    When the browser surveys the machine
    And the browser baskets ".ssh"
    Then it is refused with a warning
    And ".ssh" is back where it was

  Scenario: Insisting gets past the warning
    When the browser surveys the machine
    And the browser insists on basketing ".ssh"
    And the browser empties the basket
    Then the response says it was overridden
    And ".ssh" is gone from where it was

  Scenario: The browser can ask for duplicates
    Given a file "Downloads/report.pdf" holding "quarterly numbers"
    And a file "Archive/report-final.pdf" holding "quarterly numbers"
    When the browser surveys the machine
    And the browser asks for duplicates
    Then it is told about a set of 2 identical files
    And it is told how much deleting the copies would free

  Scenario: A folder the server never walked can still be analysed
    When the browser sends a dropped folder
    Then it gets back a plan for what was dropped
    And nothing on the server's disk was read
