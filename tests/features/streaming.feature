Feature: Reporting results while the walk is still running

  Scanning a real disk takes long enough that holding everything back until the
  end would misrepresent what is happening. The walk reports each entry the
  moment its size is known, which for a directory means after everything beneath
  it has been counted.

  Scenario: A directory is reported only once its contents are known
    Given a file "project/src/main.py" of 2 KB
    And a file "project/node_modules/react/index.js" of 300 KB
    When I walk the root
    Then "project/src" is reported before "project"
    And "project/node_modules" is reported before "project"

  Scenario: Files are reported as they are seen
    Given a file "project/data.bin" of 5 KB
    When I walk the root
    Then "project/data.bin" is reported before "project"

  Scenario: The root is always the last thing reported
    Given a file "a/one.bin" of 1 KB
    And a file "b/two.bin" of 1 KB
    When I walk the root
    Then the last report is the root

  Scenario: The final report carries the assembled tree
    Given a file "project/src/main.py" of 2 KB
    And a file "project/node_modules/react/index.js" of 300 KB
    When I walk the root
    Then the last report totals 302 KB

  Scenario: A directory that cannot be read is still reported
    Given a file "readable/notes.txt" of 10 KB
    And an unreadable directory "locked"
    When I walk the root
    Then "locked" is reported
    And "locked" is reported before the root
