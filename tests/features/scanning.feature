Feature: Scanning a directory tree

  Before Sift can say anything useful about a disk it has to know how much space
  each directory occupies — and it has to keep working when parts of the disk
  are off limits.

  Scenario: A directory reports the total size of everything beneath it
    Given a file "project/src/main.py" of 2 KB
    And a file "project/node_modules/react/index.js" of 300 KB
    And a file "project/node_modules/lodash/index.js" of 700 KB
    When I scan the root
    Then "project" reports 1002 KB
    And "project/node_modules" reports 1000 KB

  Scenario: Children are reported so the tree can be drawn
    Given a file "project/src/main.py" of 2 KB
    And a file "project/node_modules/react/index.js" of 300 KB
    When I scan the root
    Then "project" has children "node_modules, src"

  Scenario: An empty directory reports zero rather than disappearing
    Given a directory "project/empty"
    When I scan the root
    Then "project/empty" reports 0 KB

  Scenario: Sizes reflect what a file actually occupies on disk
    Given a file "project/data.bin" of 5 KB
    When I scan the root
    Then "project/data.bin" occupies at least 5 KB on disk

  Scenario: A directory Sift cannot read is reported as blocked, not as a crash
    Given a file "readable/notes.txt" of 10 KB
    And an unreadable directory "locked"
    When I scan the root
    Then the scan completes
    And "locked" is marked unreadable
    And "readable" reports 10 KB

  Scenario: Symlinked directories are not followed
    Given a file "project/real/big.bin" of 100 KB
    And a symlink "project/alias" pointing at "project/real"
    When I scan the root
    Then "project" reports 100 KB
