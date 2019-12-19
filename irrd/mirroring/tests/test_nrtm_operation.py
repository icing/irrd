from unittest.mock import Mock

from irrd.rpsl.rpsl_objects import rpsl_object_from_text
from irrd.storage.models import DatabaseOperation
from irrd.utils.rpsl_samples import SAMPLE_MNTNER, SAMPLE_UNKNOWN_CLASS, SAMPLE_MALFORMED_EMPTY_LINE, SAMPLE_KEY_CERT, \
    KEY_CERT_SIGNED_MESSAGE_VALID
from ..nrtm_operation import NRTMOperation


class TestNRTMOperation:

    def test_nrtm_add_valid_without_strict_import_keycert(self, tmp_gpg_dir):
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.add_or_update,
            serial=42424242,
            object_text=SAMPLE_KEY_CERT,
            strict_validation_key_cert=False,
            object_class_filter=['route', 'route6', 'mntner', 'key-cert'],
        )
        assert operation.save(database_handler=mock_dh)

        assert mock_dh.upsert_rpsl_object.call_count == 1
        assert mock_dh.mock_calls[0][1][0].pk() == 'PGPKEY-80F238C6'
        assert mock_dh.mock_calls[0][1][1] == 42424242

        # key-cert should not be imported in the keychain, therefore
        # verification should fail
        key_cert_obj = rpsl_object_from_text(SAMPLE_KEY_CERT, strict_validation=False)
        assert not key_cert_obj.verify(KEY_CERT_SIGNED_MESSAGE_VALID)

    def test_nrtm_add_valid_with_strict_import_keycert(self, tmp_gpg_dir):
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.add_or_update,
            serial=42424242,
            object_text=SAMPLE_KEY_CERT,
            strict_validation_key_cert=True,
            object_class_filter=['route', 'route6', 'mntner', 'key-cert'],
        )
        assert operation.save(database_handler=mock_dh)

        assert mock_dh.upsert_rpsl_object.call_count == 1
        assert mock_dh.mock_calls[0][1][0].pk() == 'PGPKEY-80F238C6'
        assert mock_dh.mock_calls[0][1][1] == 42424242

        # key-cert should be imported in the keychain, therefore
        # verification should succeed
        key_cert_obj = rpsl_object_from_text(SAMPLE_KEY_CERT, strict_validation=False)
        assert key_cert_obj.verify(KEY_CERT_SIGNED_MESSAGE_VALID)

    def test_nrtm_add_valid_ignored_object_class(self):
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.add_or_update,
            serial=42424242,
            object_text=SAMPLE_MNTNER,
            strict_validation_key_cert=False,
            object_class_filter=['route', 'route6'],
        )
        assert not operation.save(database_handler=mock_dh)
        assert mock_dh.upsert_rpsl_object.call_count == 0

    def test_nrtm_delete_valid(self):
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.delete,
            serial=42424242,
            strict_validation_key_cert=False,
            object_text=SAMPLE_MNTNER,
        )
        assert operation.save(database_handler=mock_dh)

        assert mock_dh.delete_rpsl_object.call_count == 1
        assert mock_dh.mock_calls[0][2]['rpsl_object'].pk() == 'TEST-MNT'
        assert mock_dh.mock_calls[0][2]['forced_serial'] == 42424242

    def test_nrtm_add_invalid_unknown_object_class(self):
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.add_or_update,
            serial=42424242,
            strict_validation_key_cert=False,
            object_text=SAMPLE_UNKNOWN_CLASS,
        )
        assert not operation.save(database_handler=mock_dh)
        assert mock_dh.upsert_rpsl_object.call_count == 0

    def test_nrtm_add_invalid_inconsistent_source(self):
        mock_dh = Mock()

        operation = NRTMOperation(
            source='NOT-TEST',
            operation=DatabaseOperation.add_or_update,
            serial=42424242,
            strict_validation_key_cert=False,
            object_text=SAMPLE_MNTNER,
        )
        assert not operation.save(database_handler=mock_dh)
        assert mock_dh.upsert_rpsl_object.call_count == 0

    def test_nrtm_add_invalid_rpsl_errors(self):
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.add_or_update,
            serial=42424242,
            strict_validation_key_cert=False,
            object_text=SAMPLE_MALFORMED_EMPTY_LINE,
        )
        assert not operation.save(database_handler=mock_dh)
        assert mock_dh.upsert_rpsl_object.call_count == 0

    def test_nrtm_delete_valid_incomplete_object(self):
        # In some rare cases, NRTM updates will arrive without
        # a source attribute. However, as the source of the NRTM
        # stream is known, we can guess this.
        # This is accepted for deletions only.
        obj_text = 'route: 192.0.02.0/24\norigin: AS65537'
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.delete,
            serial=42424242,
            object_text=obj_text,
            strict_validation_key_cert=False,
        )
        assert operation.save(database_handler=mock_dh)

        assert mock_dh.delete_rpsl_object.call_count == 1
        assert mock_dh.mock_calls[0][2]['rpsl_object'].pk() == '192.0.2.0/24AS65537'
        assert mock_dh.mock_calls[0][2]['forced_serial'] == 42424242

    def test_nrtm_add_invalid_incomplete_object(self):
        # Source-less objects are not accepted for add/update
        obj_text = 'route: 192.0.02.0/24\norigin: AS65537'
        mock_dh = Mock()

        operation = NRTMOperation(
            source='TEST',
            operation=DatabaseOperation.add_or_update,
            serial=42424242,
            object_text=obj_text,
            strict_validation_key_cert=False,
        )
        assert not operation.save(database_handler=mock_dh)
        assert not mock_dh.upsert_rpsl_object.call_count
