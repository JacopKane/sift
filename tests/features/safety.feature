Feature: Things that must be true whatever model is answering

  Every assertion here is a bug that actually happened. Most were found by
  swapping the model — one provider was right where another was wrong — so these
  are written as properties of the system rather than of any model, and they run
  the whole pipeline end to end: survey, catalog, model, plan, map.

  One scenario, many assertions, deliberately. The pipeline runs once and
  everything is checked against that single result, because thirteen scenarios
  would mean thirteen surveys and thirteen model calls to learn the same thing.

  @slow
  Scenario: The whole pipeline holds its guarantees
    Given a machine that looks like a developer's Mac
    When the whole pipeline runs

    # gpt-5.4-mini called src/ regenerable and offered "npm run build" as the way
    # to get it back. A build consumes source; it does not produce it.
    Then source code is never proposed for deletion
    And source code is settled without asking a model

    # A folder holding both disposable and irreplaceable things was called
    # regenerable, which proposes deleting somebody's only copy.
    And nothing holding irreplaceable things is called disposable

    # build_plan re-read sizes from the tree instead of using the candidate's, and
    # separately, colouring the tree before building the plan made every judged
    # item count twice. Both read as more bytes than the disk holds.
    And the plan never accounts for more bytes than the disk holds

    # A "loose files in X" item carried the directory's path, so approving it
    # would have deleted the irreplaceable directories beside those files.
    And nothing proposed would delete something kept back

    # A verdict with no way back withholds the one thing the user needed.
    And everything called regenerable says how to get it back

    # Classifications never reached the tree the chart reads from, so a folder the
    # catalog knows nothing about drew entirely grey.
    And the map is coloured by what was actually decided

    # The model answered about a directory nobody offered it.
    And no verdict was invented for something never offered

    # reclaimable_bytes summed every proposal, promising space that might turn out
    # to be the only copy of something.
    And the reclaimable total promises only what can be rebuilt
