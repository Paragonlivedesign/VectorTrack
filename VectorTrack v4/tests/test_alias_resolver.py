from vectortrack.services.alias_resolver import AliasResolver


def test_alias_resolver_exact_match():
    resolver = AliasResolver({"Client A": ["ClientA.vwx"]})
    match = resolver.resolve("clienta.vwx")
    assert match is not None
    assert match.canonical == "Client A"
    assert match.strategy == "exact"


def test_alias_resolver_prefix_match():
    resolver = AliasResolver({"Project Main": ["Project_Main"]})
    match = resolver.resolve("Project_Main - copy.vwx")
    assert match is not None
    assert match.canonical == "Project Main"
    assert match.strategy == "prefix"


def test_alias_resolver_pattern_match():
    resolver = AliasResolver({"Client Template": ["client_*_template.vwx"]})
    match = resolver.resolve("client_acme_template.vwx")
    assert match is not None
    assert match.canonical == "Client Template"
    assert match.strategy == "pattern"


def test_alias_resolver_version_heuristic():
    resolver = AliasResolver({"Kitchen Model": ["Kitchen Model.vwx"]})
    match = resolver.resolve("Kitchen Model v2.vwx")
    assert match is not None
    assert match.canonical == "Kitchen Model"
    assert match.strategy == "version_heuristic"


def test_alias_resolver_resolve_name_with_default():
    resolver = AliasResolver({"Client A": ["ClientA.vwx"]})
    assert resolver.resolve_name("unknown.vwx", default="fallback") == "fallback"


def test_alias_resolver_normalizes_full_paths():
    resolver = AliasResolver({"Main Job": [r"I:\Jobs\Main Job.vwx"]})
    match = resolver.resolve(r"C:\temp\MAIN JOB.vwx")
    assert match is not None
    assert match.canonical == "Main Job"


def test_alias_resolver_prefers_longer_prefix():
    resolver = AliasResolver(
        {
            "Short": ["Project"],
            "Long": ["Project_Main"],
        }
    )
    match = resolver.resolve("Project_Main - Option A.vwx")
    assert match is not None
    assert match.canonical == "Long"
    assert match.strategy == "prefix"
