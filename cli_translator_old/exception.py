class EbookTranslatorError(Exception):
    pass

class UnexpectedResult(EbookTranslatorError):
    pass

class ConversionAbort(EbookTranslatorError):
    pass
