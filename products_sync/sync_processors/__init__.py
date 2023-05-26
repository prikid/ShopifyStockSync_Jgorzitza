from abc import ABC, abstractmethod


class BaseProductsSyncProcessor(ABC):
    @abstractmethod
    def run_sync(self):
        pass