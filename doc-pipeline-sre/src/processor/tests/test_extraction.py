import pytest
import json
from unittest.mock import patch, MagicMock
from src.processor.main import lambda_handler

@pytest.fixture
def mock_sqs_event():
    return {
        "Records": [
            {
                "body": json.dumps({
                    "bucket": "pdf-pipeline-input-dev",
                    "key": "test_document.pdf"
                })
            }
        ]
    }

@patch('src.processor.main.s3_client')
@patch('src.processor.main.PdfReader')
@patch('os.path.exists', return_value=True)
@patch('os.remove')
def test_lambda_handler_success(mock_remove, mock_exists, mock_pdf_reader, mock_s3, mock_sqs_event):
    # Mocking da leitura do PDF
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Texto extraído com sucesso do PDF."
    mock_pdf_reader.return_value.pages = [mock_page]
    
    # Execução do Handler
    response = lambda_handler(mock_sqs_event, None)
    
    # Asserções
    assert response["statusCode"] == 200
    mock_s3.download_file.assert_called_once_with(
        "pdf-pipeline-input-dev", 
        "test_document.pdf", 
        "/tmp/test_document.pdf"
    )
    mock_s3.put_object.assert_called_once()

def test_lambda_handler_invalid_payload():
    invalid_event = {"Records": [{"body": json.dumps({})}]}
    
    with pytest.raises(ValueError, match="Payload inválido"):
        lambda_handler(invalid_event, None)