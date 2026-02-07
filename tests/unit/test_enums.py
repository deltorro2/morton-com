"""Unit tests for enumerations defined in src.models."""

from __future__ import annotations

import pytest

from src.models import (
    AuthState,
    ConflictResolution,
    OperationType,
    SourceType,
    TransferStatus,
)


class TestSourceType:
    """Tests for SourceType enumeration."""

    def test_source_type_has_expected_members(self) -> None:
        """SourceType should have exactly LOCAL, GCS_PROJECT, and GCS_BUCKET members."""
        expected_members = {"LOCAL", "GCS_PROJECT", "GCS_BUCKET"}
        actual_members = {member.name for member in SourceType}
        assert actual_members == expected_members

    def test_source_type_values(self) -> None:
        """SourceType members should have correct string values."""
        assert SourceType.LOCAL.value == "local"
        assert SourceType.GCS_PROJECT.value == "gcs_project"
        assert SourceType.GCS_BUCKET.value == "gcs_bucket"

    def test_source_type_membership(self) -> None:
        """SourceType membership checks should work correctly."""
        assert SourceType.LOCAL in SourceType
        assert SourceType.GCS_PROJECT in SourceType
        assert SourceType.GCS_BUCKET in SourceType

    def test_source_type_value_uniqueness(self) -> None:
        """All SourceType values should be unique."""
        values = [member.value for member in SourceType]
        assert len(values) == len(set(values))

    def test_source_type_string_representation(self) -> None:
        """SourceType string representation should be accessible."""
        assert str(SourceType.LOCAL) == "SourceType.LOCAL"
        assert SourceType.LOCAL.name == "LOCAL"


class TestOperationType:
    """Tests for OperationType enumeration."""

    def test_operation_type_has_expected_members(self) -> None:
        """OperationType should have exactly COPY and MOVE members."""
        expected_members = {"COPY", "MOVE"}
        actual_members = {member.name for member in OperationType}
        assert actual_members == expected_members

    def test_operation_type_values(self) -> None:
        """OperationType members should have correct string values."""
        assert OperationType.COPY.value == "copy"
        assert OperationType.MOVE.value == "move"

    def test_operation_type_membership(self) -> None:
        """OperationType membership checks should work correctly."""
        assert OperationType.COPY in OperationType
        assert OperationType.MOVE in OperationType

    def test_operation_type_value_uniqueness(self) -> None:
        """All OperationType values should be unique."""
        values = [member.value for member in OperationType]
        assert len(values) == len(set(values))

    def test_operation_type_string_representation(self) -> None:
        """OperationType string representation should be accessible."""
        assert str(OperationType.COPY) == "OperationType.COPY"
        assert OperationType.MOVE.name == "MOVE"


class TestTransferStatus:
    """Tests for TransferStatus enumeration."""

    def test_transfer_status_has_expected_members(self) -> None:
        """TransferStatus should have all expected status members."""
        expected_members = {"PENDING", "RUNNING", "PAUSED", "COMPLETED", "FAILED", "CANCELLED"}
        actual_members = {member.name for member in TransferStatus}
        assert actual_members == expected_members

    def test_transfer_status_values(self) -> None:
        """TransferStatus members should have correct string values."""
        assert TransferStatus.PENDING.value == "pending"
        assert TransferStatus.RUNNING.value == "running"
        assert TransferStatus.PAUSED.value == "paused"
        assert TransferStatus.COMPLETED.value == "completed"
        assert TransferStatus.FAILED.value == "failed"
        assert TransferStatus.CANCELLED.value == "cancelled"

    def test_transfer_status_membership(self) -> None:
        """TransferStatus membership checks should work correctly."""
        for status in TransferStatus:
            assert status in TransferStatus

    def test_transfer_status_value_uniqueness(self) -> None:
        """All TransferStatus values should be unique."""
        values = [member.value for member in TransferStatus]
        assert len(values) == len(set(values))

    def test_transfer_status_string_representation(self) -> None:
        """TransferStatus string representation should be accessible."""
        assert str(TransferStatus.PENDING) == "TransferStatus.PENDING"
        assert TransferStatus.COMPLETED.name == "COMPLETED"


class TestConflictResolution:
    """Tests for ConflictResolution enumeration."""

    def test_conflict_resolution_has_expected_members(self) -> None:
        """ConflictResolution should have all expected resolution members."""
        expected_members = {"OVERWRITE", "SKIP", "RENAME", "ASK"}
        actual_members = {member.name for member in ConflictResolution}
        assert actual_members == expected_members

    def test_conflict_resolution_values(self) -> None:
        """ConflictResolution members should have correct string values."""
        assert ConflictResolution.OVERWRITE.value == "overwrite"
        assert ConflictResolution.SKIP.value == "skip"
        assert ConflictResolution.RENAME.value == "rename"
        assert ConflictResolution.ASK.value == "ask"

    def test_conflict_resolution_membership(self) -> None:
        """ConflictResolution membership checks should work correctly."""
        for resolution in ConflictResolution:
            assert resolution in ConflictResolution

    def test_conflict_resolution_value_uniqueness(self) -> None:
        """All ConflictResolution values should be unique."""
        values = [member.value for member in ConflictResolution]
        assert len(values) == len(set(values))

    def test_conflict_resolution_string_representation(self) -> None:
        """ConflictResolution string representation should be accessible."""
        assert str(ConflictResolution.OVERWRITE) == "ConflictResolution.OVERWRITE"
        assert ConflictResolution.ASK.name == "ASK"


class TestAuthState:
    """Tests for AuthState enumeration."""

    def test_auth_state_has_expected_members(self) -> None:
        """AuthState should have all expected authentication state members."""
        expected_members = {"SIGNED_OUT", "SIGNING_IN", "SIGNED_IN", "REFRESHING"}
        actual_members = {member.name for member in AuthState}
        assert actual_members == expected_members

    def test_auth_state_values(self) -> None:
        """AuthState members should have correct string values."""
        assert AuthState.SIGNED_OUT.value == "signed_out"
        assert AuthState.SIGNING_IN.value == "signing_in"
        assert AuthState.SIGNED_IN.value == "signed_in"
        assert AuthState.REFRESHING.value == "refreshing"

    def test_auth_state_membership(self) -> None:
        """AuthState membership checks should work correctly."""
        for state in AuthState:
            assert state in AuthState

    def test_auth_state_value_uniqueness(self) -> None:
        """All AuthState values should be unique."""
        values = [member.value for member in AuthState]
        assert len(values) == len(set(values))

    def test_auth_state_string_representation(self) -> None:
        """AuthState string representation should be accessible."""
        assert str(AuthState.SIGNED_OUT) == "AuthState.SIGNED_OUT"
        assert AuthState.SIGNED_IN.name == "SIGNED_IN"
