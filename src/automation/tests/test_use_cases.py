"""
Тесты для use cases
"""
import pytest
from unittest.mock import Mock, MagicMock
from decimal import Decimal
from datetime import date

from automation.app.use_cases import EmailProcessingUseCase, ProcessingResult
from automation.domain.models import Invoice
from automation.ports.email import EmailMessage, EmailAttachment


@pytest.fixture
def mock_dependencies():
    """Создать mock объекты для зависимостей"""
    return {
        'email_processor': Mock(),
        'repository': Mock(),
        'document_parser': Mock(), 
        'file_storage': Mock()
    }


@pytest.fixture
def sample_invoice():
    """Создать тестовый счет"""
    return Invoice(
        partner_id="test_partner",
        invoice_number="INV-2024-001",
        invoice_date=date(2024, 2, 20),
        amount=Decimal("150.00"),
        currency="EUR",
        source_message_id="test-message-id"
    )


@pytest.fixture 
def sample_email_message():
    """Создать тестовое email сообщение с вложением"""
    attachment = EmailAttachment(
        filename="invoice.pdf",
        content_type="application/pdf",
        content=b"fake pdf content",
        size=1024
    )
    
    return EmailMessage(
        message_id="test-msg-1",
        subject="Invoice from supplier",
        sender="supplier@example.com",
        received_date="2024-02-20T10:00:00Z",
        body="Please find attached invoice",
        attachments=[attachment]
    )


class TestEmailProcessingUseCase:
    """Тесты для EmailProcessingUseCase"""
    
    def test_process_new_emails_success(self, mock_dependencies, sample_email_message, sample_invoice):
        """Тест успешной обработки email"""
        
        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)
        
        # Setup mocks
        mock_dependencies['email_processor'].fetch_new_messages.return_value = [sample_email_message]
        mock_dependencies['file_storage'].store_safe.return_value = "/path/to/file.pdf"
        
        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies['document_parser'].parse_invoice.return_value = parse_result
        
        mock_dependencies['repository'].claim.return_value = True
        
        # Act
        result = use_case.process_new_emails()
        
        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.messages_processed == 1
        assert result.invoices_found == 1
        assert result.invoices_uploaded == 1
        assert len(result.errors) == 0
        
        # Verify mocks were called
        mock_dependencies['email_processor'].fetch_new_messages.assert_called_once()
        mock_dependencies['repository'].claim.assert_called_once_with(sample_invoice.invoice_key)
        mock_dependencies['repository'].mark_done.assert_called_once_with(sample_invoice.invoice_key)
    
    def test_process_new_emails_duplicate_invoice(self, mock_dependencies, sample_email_message, sample_invoice):
        """Тест обработки дублированного счета"""
        
        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)
        
        mock_dependencies['email_processor'].fetch_new_messages.return_value = [sample_email_message]
        mock_dependencies['file_storage'].store_safe.return_value = "/path/to/file.pdf"
        
        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies['document_parser'].parse_invoice.return_value = parse_result
        
        # Имитируем, что счет уже обработан
        mock_dependencies['repository'].claim.return_value = False
        
        # Act
        result = use_case.process_new_emails()
        
        # Assert
        assert result.messages_processed == 1
        assert result.invoices_found == 1
        assert result.invoices_uploaded == 0  # Дубликат не загружен
        
        # mark_done не должен вызываться для дубликатов
        mock_dependencies['repository'].mark_done.assert_not_called()
    
    def test_process_new_emails_parsing_failure(self, mock_dependencies, sample_email_message):
        """Тест обработки ошибки парсинга"""
        
        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)
        
        mock_dependencies['email_processor'].fetch_new_messages.return_value = [sample_email_message]
        mock_dependencies['file_storage'].store_safe.return_value = "/path/to/file.pdf"
        
        # Имитируем ошибку парсинга
        parse_result = Mock()
        parse_result.success = False
        parse_result.invoice = None
        mock_dependencies['document_parser'].parse_invoice.return_value = parse_result
        
        # Act
        result = use_case.process_new_emails()
        
        # Assert
        assert result.messages_processed == 1
        assert result.invoices_found == 0
        assert result.invoices_uploaded == 0
        
        # repository.claim не должен вызываться при ошибке парсинга
        mock_dependencies['repository'].claim.assert_not_called()
    
    def test_process_new_emails_dry_run(self, mock_dependencies, sample_email_message, sample_invoice):
        """Тест dry run режима"""
        
        # Arrange  
        use_case = EmailProcessingUseCase(**mock_dependencies)
        
        mock_dependencies['email_processor'].fetch_new_messages.return_value = [sample_email_message]
        
        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies['document_parser'].parse_invoice.return_value = parse_result
        
        mock_dependencies['repository'].claim.return_value = True
        
        # Act
        result = use_case.process_new_emails(dry_run=True)
        
        # Assert
        assert result.messages_processed == 1
        assert result.invoices_found == 1
        assert result.invoices_uploaded == 1  # Считается "загруженным" в dry run
        
        # В dry run режиме не должны выполняться реальные операции
        mock_dependencies['file_storage'].store_safe.assert_not_called()
        mock_dependencies['repository'].mark_done.assert_not_called()
    
    def test_process_new_emails_exception_handling(self, mock_dependencies, sample_email_message):
        """Тест обработки исключений"""
        
        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)
        
        mock_dependencies['email_processor'].fetch_new_messages.return_value = [sample_email_message]
        
        # Имитируем исключение при обработке
        mock_dependencies['file_storage'].store_safe.side_effect = Exception("Storage error")
        
        # Act
        result = use_case.process_new_emails()
        
        # Assert
        assert result.messages_processed == 1
        assert len(result.errors) == 1
        assert "Storage error" in result.errors[0]
        assert result.invoices_uploaded == 0


@pytest.mark.integration
class TestEmailProcessingIntegration:
    """Интеграционные тесты для обработки email"""
    
    def test_full_processing_workflow(self):
        """Тест полного workflow обработки"""
        # Здесь будут интеграционные тесты с реальными компонентами
        pass