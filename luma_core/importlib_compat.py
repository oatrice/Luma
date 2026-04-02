try:
    import importlib.metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata  # type: ignore[no-redef]


def ensure_importlib_metadata_compat(metadata_module=None):
    """Backfill Python 3.9's missing packages_distributions helper."""
    metadata_module = metadata_module or importlib_metadata
    if hasattr(metadata_module, "packages_distributions"):
        return False

    def packages_distributions():
        module_to_distributions = {}
        try:
            for distribution in metadata_module.distributions():
                try:
                    distribution_name = distribution.metadata.get("Name")
                except Exception:
                    distribution_name = None

                if not distribution_name:
                    continue

                for file_entry in getattr(distribution, "files", ()) or ():
                    parts = getattr(file_entry, "parts", None)
                    if not parts:
                        continue
                    module_to_distributions.setdefault(parts[0], []).append(
                        distribution_name
                    )
        except Exception:
            return {}

        return module_to_distributions

    metadata_module.packages_distributions = packages_distributions
    return True


ensure_importlib_metadata_compat()
