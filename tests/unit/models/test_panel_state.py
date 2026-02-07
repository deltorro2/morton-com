"""Unit tests for PanelState dataclass."""

from __future__ import annotations

import pytest

from src.models import SourceType
from src.models.panel_state import PanelState


class TestPanelStateRequiredFields:
    """Tests for PanelState with required fields only."""

    def test_create_with_required_fields_only(self) -> None:
        """PanelState can be created with only id and source_type."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)

        assert state.id == "left"
        assert state.source_type == SourceType.LOCAL

    def test_required_fields_are_mandatory(self) -> None:
        """PanelState raises TypeError when required fields are missing."""
        with pytest.raises(TypeError):
            PanelState()  # type: ignore[call-arg]

        with pytest.raises(TypeError):
            PanelState(id="left")  # type: ignore[call-arg]

        with pytest.raises(TypeError):
            PanelState(source_type=SourceType.LOCAL)  # type: ignore[call-arg]


class TestPanelStateDefaultValues:
    """Tests for PanelState default field values."""

    def test_location_defaults_to_empty_string(self) -> None:
        """location defaults to empty string."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.location == ""

    def test_project_id_defaults_to_empty_string(self) -> None:
        """project_id defaults to empty string."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.project_id == ""

    def test_bucket_name_defaults_to_empty_string(self) -> None:
        """bucket_name defaults to empty string."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.bucket_name == ""

    def test_items_defaults_to_empty_list(self) -> None:
        """items defaults to empty list."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.items == []
        assert isinstance(state.items, list)

    def test_selected_indices_defaults_to_empty_set(self) -> None:
        """selected_indices defaults to empty set."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.selected_indices == set()
        assert isinstance(state.selected_indices, set)

    def test_sort_column_defaults_to_name(self) -> None:
        """sort_column defaults to 'name'."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.sort_column == "name"

    def test_sort_ascending_defaults_to_true(self) -> None:
        """sort_ascending defaults to True."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.sort_ascending is True

    def test_loading_defaults_to_false(self) -> None:
        """loading defaults to False."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.loading is False

    def test_error_defaults_to_empty_string(self) -> None:
        """error defaults to empty string."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        assert state.error == ""


class TestPanelStateAllFields:
    """Tests for PanelState with all fields specified."""

    def test_create_with_all_fields(self) -> None:
        """PanelState can be created with all fields specified."""
        items = [{"name": "file1.txt"}, {"name": "file2.txt"}]
        selected = {0, 1}

        state = PanelState(
            id="right",
            source_type=SourceType.GCS_BUCKET,
            location="/path/to/folder",
            project_id="my-gcp-project",
            bucket_name="my-bucket",
            items=items,
            selected_indices=selected,
            sort_column="size",
            sort_ascending=False,
            loading=True,
            error="Connection timeout",
        )

        assert state.id == "right"
        assert state.source_type == SourceType.GCS_BUCKET
        assert state.location == "/path/to/folder"
        assert state.project_id == "my-gcp-project"
        assert state.bucket_name == "my-bucket"
        assert state.items == items
        assert state.selected_indices == selected
        assert state.sort_column == "size"
        assert state.sort_ascending is False
        assert state.loading is True
        assert state.error == "Connection timeout"


class TestPanelStateSourceTypes:
    """Tests for PanelState with different SourceType values."""

    def test_with_source_type_local(self) -> None:
        """PanelState works with SourceType.LOCAL."""
        state = PanelState(
            id="left",
            source_type=SourceType.LOCAL,
            location="/home/user/documents",
        )

        assert state.source_type == SourceType.LOCAL
        assert state.source_type.value == "local"

    def test_with_source_type_gcs_project(self) -> None:
        """PanelState works with SourceType.GCS_PROJECT."""
        state = PanelState(
            id="right",
            source_type=SourceType.GCS_PROJECT,
            project_id="my-gcp-project",
        )

        assert state.source_type == SourceType.GCS_PROJECT
        assert state.source_type.value == "gcs_project"

    def test_with_source_type_gcs_bucket(self) -> None:
        """PanelState works with SourceType.GCS_BUCKET."""
        state = PanelState(
            id="right",
            source_type=SourceType.GCS_BUCKET,
            project_id="my-gcp-project",
            bucket_name="my-bucket",
            location="path/to/prefix/",
        )

        assert state.source_type == SourceType.GCS_BUCKET
        assert state.source_type.value == "gcs_bucket"


class TestPanelStateMutableDefaults:
    """Tests to verify mutable default values are properly isolated."""

    def test_items_list_is_not_shared_between_instances(self) -> None:
        """Each PanelState instance has its own items list."""
        state1 = PanelState(id="left", source_type=SourceType.LOCAL)
        state2 = PanelState(id="right", source_type=SourceType.LOCAL)

        state1.items.append({"name": "file.txt"})

        assert state1.items == [{"name": "file.txt"}]
        assert state2.items == []

    def test_selected_indices_set_is_not_shared_between_instances(self) -> None:
        """Each PanelState instance has its own selected_indices set."""
        state1 = PanelState(id="left", source_type=SourceType.LOCAL)
        state2 = PanelState(id="right", source_type=SourceType.LOCAL)

        state1.selected_indices.add(0)

        assert state1.selected_indices == {0}
        assert state2.selected_indices == set()


class TestPanelStateDataclassBehavior:
    """Tests for dataclass-specific behavior of PanelState."""

    def test_equality_comparison(self) -> None:
        """Two PanelState instances with same values are equal."""
        state1 = PanelState(id="left", source_type=SourceType.LOCAL)
        state2 = PanelState(id="left", source_type=SourceType.LOCAL)

        assert state1 == state2

    def test_inequality_comparison(self) -> None:
        """Two PanelState instances with different values are not equal."""
        state1 = PanelState(id="left", source_type=SourceType.LOCAL)
        state2 = PanelState(id="right", source_type=SourceType.LOCAL)

        assert state1 != state2

    def test_repr_contains_field_values(self) -> None:
        """PanelState repr contains field names and values."""
        state = PanelState(id="left", source_type=SourceType.LOCAL)
        repr_str = repr(state)

        assert "PanelState" in repr_str
        assert "id='left'" in repr_str
        assert "SourceType.LOCAL" in repr_str
