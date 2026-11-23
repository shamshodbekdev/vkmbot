from aiogram.filters.callback_data import CallbackData


class BulkDownloadCallback(CallbackData, prefix="blkdl"):
    """Field-less callback: the bulk download button carries no data."""
