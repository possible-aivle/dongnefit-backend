# Local API Endpoint Deletion Analysis

## Overview
Comprehensive mapping of all files that use local-endpoint-related items from '@dongnefit/shared' in the frontend client app.

## Files Using Local API Imports

### Category 1: Files ONLY Using Local API (Candidates for Deletion)
These files exclusively use local API imports and have NO other external dependencies on non-local features.

1. **apps/client/src/pages/home-map-page/ui/home-map-page.tsx**
   - Uses: `searchLotsApiV1LocalLotsSearchGet`
   - Type imports: None specific, uses lot search results
   - Status: ONLY local usage
   - Imported by: router.tsx (main route), features/map-filter (indirectly via MapFilterPanel)

2. **apps/client/src/features/map-filter/ui/map-filter-panel.tsx**
   - Uses: `getLotFilterOptionsApiV1LocalLotsFilterOptionsGet`, `getGetLotFilterOptionsApiV1LocalLotsFilterOptionsGetQueryKey`
   - Type imports: None (returns LotFilterOptionsResponse implicitly)
   - Status: ONLY local usage
   - Imported by: home-map-page.tsx (via direct import)

3. **apps/client/src/modules/react-naver-map/lib/geojson-to-polygon.ts**
   - Uses: `MapResponseFeaturesItem` (type only)
   - Functions: `mapResponseToFeatures()` (pure utility)
   - Status: ONLY local type usage
   - Imported by: react-naver-map.tsx, property-map-container.tsx

### Category 2: Files Mixing Local + Non-Local Imports (Need Surgical Editing)
These files use local API imports BUT also have other functionality that must be preserved.

1. **apps/client/src/modules/react-naver-map/ui/property-map-container.tsx**
   - Local API uses:
     * `getGetMapBuildingsApiV1LocalMapBuildingsGetQueryKey`
     * `getGetMapLotsApiV1LocalMapLotsGetQueryKey`
     * `getMapBuildingsApiV1LocalMapBuildingsGet`
     * `getMapLotsApiV1LocalMapLotsGet`
     * `searchLotsApiV1LocalLotsSearchGet`
     * `getLotDetailApiV1LocalLotsPnuGet`
     * `getGetLotDetailApiV1LocalLotsPnuGetQueryKey`
   - Non-local dependencies: useNaverMapStore, naver-map setup, map interaction logic
   - Status: MIXED - needs surgical removal of local API calls only
   - Imported by: router.tsx (as PropertyMapContainer from main module)
   
2. **apps/client/src/features/property-detail/ui/transaction-section.tsx**
   - Local API uses:
     * `getTransactionsApiV1LocalTransactionsGet`
     * `getGetTransactionsApiV1LocalTransactionsGetQueryKey`
     * Type: `GetTransactionsApiV1LocalTransactionsGetParams`, `PropertyType`, `TransactionType`
   - Non-local dependencies: UI components (Select, Separator, Skeleton), business logic (formatting, filtering)
   - Status: MIXED - needs surgical removal
   - Imported by: property-detail-panel.tsx

3. **apps/client/src/features/property-detail/ui/lot-info-section.tsx**
   - Local API uses: Type only - `LotDetailResponse`
   - Non-local dependencies: UI display logic, formatting utilities
   - Status: MIXED - type import removal only (no functional code to remove)
   - Imported by: property-detail-panel.tsx

4. **apps/client/src/features/property-detail/ui/building-info-section.tsx**
   - Local API uses: Type only - `BuildingDetailResponse`
   - Non-local dependencies: UI display logic, formatting utilities
   - Status: MIXED - type import removal only
   - Imported by: property-detail-panel.tsx

5. **apps/client/src/features/property-detail/ui/property-summary-card.tsx**
   - Local API uses: Type only - `PropertySummaryResponse`
   - Non-local dependencies: UI display logic, formatting utilities
   - Status: MIXED - type import removal only
   - Imported by: property-detail-panel.tsx

6. **apps/client/src/features/property-detail/ui/property-detail-panel.tsx**
   - Local API uses:
     * `useGetBuildingDetailApiV1LocalBuildingsPnuGet` (hook)
     * `useGetLotDetailApiV1LocalLotsPnuGet` (hook)
     * `useGetPropertySummaryApiV1LocalPropertiesPnuSummaryGet` (hook)
   - Non-local dependencies: Local child components (lot-info, building-info, summary-card, transaction), UI layout
   - Status: MIXED - core orchestration component
   - Imported by: router.tsx (via features/property-detail index.ts)

### Category 3: Re-export/Index Files (For Module Export Management)
1. **apps/client/src/features/property-detail/index.ts**
   - Exports: PropertyDetailPanel
   - Status: Indirect dependency - affected if property-detail-panel is deleted

2. **apps/client/src/features/map-filter/index.ts**
   - Exports: MapFilterPanel
   - Status: Indirect dependency

3. **apps/client/src/modules/react-naver-map/index.ts**
   - Exports: ReactNaverMap, PropertyMapContainer, geojson-to-polygon utilities
   - Status: Indirect dependency

4. **apps/client/src/pages/home-map-page/index.ts**
   - Exports: HomeMapPage
   - Status: Indirect dependency

## Import Chain (Dependency Graph)

```
router.tsx (main entry point)
├── HomeMapPage (pages/home-map-page)
│   └── MapFilterPanel (features/map-filter) ← LOCAL ONLY
│   └── searchLotsApiV1LocalLotsSearchGet ← LOCAL ONLY
│
├── PropertyDetailPanel (features/property-detail)
│   ├── useGetLotDetailApiV1LocalLotsPnuGet ← LOCAL API
│   ├── useGetBuildingDetailApiV1LocalBuildingsPnuGet ← LOCAL API
│   ├── useGetPropertySummaryApiV1LocalPropertiesPnuSummaryGet ← LOCAL API
│   └── Child components (all consume local types):
│       ├── LotInfoSection (uses LotDetailResponse)
│       ├── BuildingInfoSection (uses BuildingDetailResponse)
│       ├── PropertySummaryCard (uses PropertySummaryResponse)
│       └── TransactionSection
│           └── getTransactionsApiV1LocalTransactionsGet ← LOCAL API
│
└── PropertyMapContainer (modules/react-naver-map)
    ├── Uses local map APIs (getMapLotsApiV1LocalMapLotsGet, etc.) ← LOCAL API
    ├── searchLotsApiV1LocalLotsSearchGet ← LOCAL API
    ├── getLotDetailApiV1LocalLotsPnuGet ← LOCAL API
    └── ReactNaverMap (child)
        └── mapResponseToFeatures (uses MapResponseFeaturesItem type) ← LOCAL TYPE
```

## Local API Functions & Types Used (Complete List)

### Functions
- `searchLotsApiV1LocalLotsSearchGet` - search lots by location/coords
- `getMapLotsApiV1LocalMapLotsGet` - fetch lots for map bounds
- `getMapBuildingsApiV1LocalMapBuildingsGet` - fetch buildings for map
- `getLotDetailApiV1LocalLotsPnuGet` - fetch single lot detail
- `getTransactionsApiV1LocalTransactionsGet` - fetch transactions
- `getLotFilterOptionsApiV1LocalLotsFilterOptionsGet` - fetch filter options

### Query Key Generators
- `getGetMapBuildingsApiV1LocalMapBuildingsGetQueryKey`
- `getGetMapLotsApiV1LocalMapLotsGetQueryKey`
- `getGetLotDetailApiV1LocalLotsPnuGetQueryKey`
- `getGetTransactionsApiV1LocalTransactionsGetQueryKey`
- `getGetLotFilterOptionsApiV1LocalLotsFilterOptionsGetQueryKey`

### Types
- `LotDetailResponse` - returned by getLotDetailApiV1LocalLotsPnuGet
- `BuildingDetailResponse` - returned by useGetBuildingDetailApiV1LocalBuildingsPnuGet
- `PropertySummaryResponse` - returned by useGetPropertySummaryApiV1LocalPropertiesPnuSummaryGet
- `MapResponseFeaturesItem` - GeoJSON feature type from map API responses
- `GetTransactionsApiV1LocalTransactionsGetParams` - parameter type for transactions
- `PropertyType` - enum/type
- `TransactionType` - enum/type

## Deletion Strategy

### Phase 1: Delete Files ONLY Using Local APIs
- Delete: `apps/client/src/pages/home-map-page/` (entire directory)
- Delete: `apps/client/src/features/map-filter/` (entire directory)
- Delete or keep `geojson-to-polygon.ts` utility as it's a pure converter (optional)

### Phase 2: Remove Local Imports from Mixed-Use Files
- **property-detail-panel.tsx**: Remove 3 useGet hooks, remove child component imports, remove Tabs UI
- **transaction-section.tsx**: Remove getTransactionsApiV1LocalTransactionsGet calls, remove transaction display
- **property-detail/* children**: Remove type imports (LotDetailResponse, BuildingDetailResponse, PropertySummaryResponse)
- **property-map-container.tsx**: Remove all 7 local API queries, keep map interaction logic

### Phase 3: Update Router & Entry Points
- Remove HomeMapPage route from router.tsx
- Remove PropertyMapContainer from main layout OR replace with placeholder
- Update module exports in index.ts files

## Critical Dependencies to Preserve
1. **UI Component Library** - shadcn/ui, Lucide icons (NOT local API)
2. **State Management** - useNaverMapStore (non-local)
3. **Map Rendering** - react-naver-maps library
4. **Type System** - TanStack Query types, React types
5. **Business Logic** - Formatting utilities, event handlers

## Estimated Impact
- Files to delete: 2 directories (home-map-page, map-filter)
- Files to modify: 6 files (property-detail-panel, transaction-section, 4 info sections, property-map-container)
- Index files affected: 4 (for re-exports)
- Routes affected: Primary route (/) removed from feature
- Core functionality removed: Local data browsing, property detail panels, map search
