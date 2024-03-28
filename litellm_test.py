import litellm
from litellm_test import completion
from litellm.caching import Cache
litellm_test.cache = Cache()