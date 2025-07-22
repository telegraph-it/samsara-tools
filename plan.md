# Samsara API Tools - Architectural Restructuring Plan

## Overview
This plan outlines the transformation of the current script-based Samsara API toolkit into a well-architected Python library with proper separation of concerns, type safety, and maintainability.

## Current State
- Script-based approach with legacy files in `/legacy/`
- Direct API calls mixed with business logic
- Limited type safety and code reuse
- Duplicated utilities (rate limiting, caching)

## Target Architecture
**Layered Architecture:**
- **Presentation**: CLI (argparse, future Typer support)
- **Service**: High-level business actions (GeofenceService, GatewayService, TagService)
- **Infrastructure**: HTTP, cache, rate-limit, auth, env, persistence
- **Domain**: Typed, serializable models (Pydantic)

## Implementation Plan

### Phase 1: Infrastructure Foundation (High Priority)

#### Step 1: Create Infrastructure Modules
- **`infrastructure/cache.py`** - Move CacheManager from client.py
  - Extract existing CacheManager class
  - Improve interface with proper typing
  - Add TTL configuration support

- **`infrastructure/rate_limiter.py`** - Move RateLimiter from client.py
  - Extract existing RateLimiter class
  - Add exponential backoff with jitter
  - Context manager support for retry loops

- **`infrastructure/http_client.py`** - New HTTP abstraction layer
  - Centralized HTTP client with auth injection
  - Automatic pagination support
  - Integrated rate limiting
  - Error handling and retry logic

#### Step 2: Create Typed Models
- **`models/gateway.py`** - Gateway and ConnectionStatus models
  ```python
  class ConnectionStatus(BaseModel):
      healthStatus: Literal["healthy", "unhealthy"]
      lastConnected: Optional[datetime]
  
  class Gateway(BaseModel):
      id: str
      serial: str
      model: str
      connectionStatus: ConnectionStatus
  ```

- **`models/tag.py`** - Tag model
  ```python
  class Tag(BaseModel):
      id: str
      name: str
      createdAtTime: Optional[datetime]
  ```

- **`models/geofence.py`** - Geofence and Address models
  ```python
  class Geofence(BaseModel):
      id: str
      name: str
      address: Address
      geofenceType: GeofenceType
  ```

#### Step 3: Create Service Layer
- **`services/gateway.py`** - GatewayService
  ```python
  class GatewayService:
      def list_gateways(self, *, refresh: bool = False) -> List[Gateway]
  ```

- **`services/tag.py`** - TagService
  ```python
  class TagService:
      def list_tags(self) -> List[Tag]
      def find(self, name: str) -> Optional[Tag]
  ```

- **`services/geofence.py`** - GeofenceService
  ```python
  class GeofenceService:
      def query_by_tag(self, tag_name: str) -> List[Geofence]
      def save(self, geofences: List[Geofence], *, fmt: Literal["csv","json"]) -> Path
      def summary(self, geofences: List[Geofence]) -> str
  ```

### Phase 2: Configuration & Utilities (Medium Priority)

#### Step 4: Create Configuration Module
- **`config.py`** - Centralize all configuration constants
  ```python
  BASE_URL = os.getenv("SAMSARA_BASE_URL", "https://api.samsara.com")
  CACHE_DIR = Path(os.getenv("SAMSARA_CACHE_DIR", "data/cache"))
  CACHE_TTL = timedelta(hours=1)
  OUTPUT_DIR = Path("data/output")
  ```

#### Step 5: Create Logging Utility
- **`utils/logging.py`** - Centralized logger factory
  ```python
  def get_logger(name: str, level: Union[str, int] = logging.INFO) -> logging.Logger
  ```

#### Step 6: Update Dependencies
- Add `pydantic>=2.0` to requirements.txt
- Update pyproject.toml with new dependencies
- Add development extras for testing

### Phase 3: Migration & Integration (High Priority)

#### Step 7: Migrate Existing Logic
- Move logic from `core/client.py` to new infrastructure and services
- Replace direct requests calls with HttpClient
- Update import paths throughout codebase
- Remove duplicated code

#### Step 8: Update CLI Interface
- Update `cli/main.py` to use new service layer
- Replace direct SamsaraClient calls with services
- Maintain identical CLI behavior and arguments
- Add proper dependency injection

#### Step 9: Update Public API
- Clean up `__init__.py` exports
- Export only Services and models
- Add proper `__all__` declarations
- Remove internal implementation details

### Phase 4: Cleanup & Testing (Medium/Low Priority)

#### Step 10: Add Deprecation Warnings
- Mark `core/client.py` as deprecated
- Mark `core/geofence_query.py` as deprecated
- Add backward compatibility shims
- Plan removal timeline

#### Step 11: Test CLI Functionality
- Verify all existing CLI commands work identically
- Test with real API calls
- Validate output formats match existing behavior
- Check error handling scenarios

#### Step 12: Run Type Checking
- Add mypy configuration
- Run `mypy --strict` on entire codebase
- Fix any type inconsistencies
- Add type annotations where missing

## File Structure After Implementation

```
src/samsara_tools/
├── __init__.py                    # Clean public API exports
├── config.py                      # Centralized configuration
├── cli/
│   ├── __init__.py
│   └── main.py                    # Updated to use services
├── infrastructure/
│   ├── __init__.py
│   ├── cache.py                   # Extracted CacheManager
│   ├── rate_limiter.py            # Extracted RateLimiter
│   └── http_client.py             # New HTTP abstraction
├── services/
│   ├── __init__.py
│   ├── gateway.py                 # GatewayService
│   ├── tag.py                     # TagService
│   └── geofence.py                # GeofenceService
├── models/
│   ├── __init__.py
│   ├── gateway.py                 # Gateway models
│   ├── tag.py                     # Tag models
│   └── geofence.py                # Geofence models
├── utils/
│   ├── __init__.py
│   └── logging.py                 # Centralized logging
└── core/                          # Deprecated modules
    ├── __init__.py
    ├── client.py                  # Marked deprecated
    └── geofence_query.py          # Marked deprecated
```

## Benefits of This Restructuring

1. **Maintainability**: Clear separation of concerns with proper abstraction layers
2. **Type Safety**: Pydantic models ensure data integrity throughout the system
3. **Reusability**: Service layer can be used by CLI, web interfaces, or other applications
4. **Testability**: Each layer can be tested independently with proper mocking
5. **Extensibility**: Easy to add new features without touching existing code
6. **Performance**: Centralized caching and rate limiting prevent redundant API calls
7. **Developer Experience**: Better IDE support with proper typing and imports

## Migration Strategy

- **Backward Compatibility**: Maintain existing CLI behavior during transition
- **Incremental Changes**: Each phase can be implemented and tested independently
- **Deprecation Path**: Old modules remain functional with warnings until v1.0.0
- **Documentation**: Update examples and README to use new API patterns

## Success Criteria

- [ ] All existing CLI commands work identically
- [ ] Type checking passes with `mypy --strict`
- [ ] No performance regression in API calls
- [ ] Clean public API with proper exports
- [ ] Comprehensive test coverage for new modules
- [ ] Documentation updated with new architecture