"""Neo4j graph service for zone relationships, routing, and spatial queries.

Data Science Theory:
- Dijkstra's Algorithm: Shortest path for routing vehicles to available zones
- Community Detection (Louvain): Grouping related zones for management
- Betweenness Centrality: Identifying critical junction zones
- PageRank: Ranking zones by traffic flow importance
"""

from typing import List, Dict, Optional, Tuple
from loguru import logger


class ParkingGraphService:
    """Neo4j-based graph operations for parking zone management."""

    def __init__(self, neo4j_session):
        self.session = neo4j_session

    # ─── Schema Setup ──────────────────────────────────────────────────

    async def init_graph(self):
        """Create constraints and indexes for the parking graph."""
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (z:Zone) REQUIRE z.code IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entrance) REQUIRE e.name IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (z:Zone) ON (z.occupancy_rate)",
        ]
        for q in queries:
            await self.session.run(q)
        logger.info("Neo4j graph schema initialized")

    # ─── Zone Node Management ──────────────────────────────────────────

    async def upsert_zone(
        self, code: str, name: str, total_spots: int,
        occupied: int, lat: float, lon: float, floor: int
    ):
        """Create or update a zone node with current state."""
        query = """
        MERGE (z:Zone {code: $code})
        SET z.name = $name,
            z.total_spots = $total_spots,
            z.occupied = $occupied,
            z.available = $total_spots - $occupied,
            z.occupancy_rate = CASE WHEN $total_spots > 0
                THEN toFloat($occupied) / $total_spots * 100 ELSE 0 END,
            z.latitude = $lat,
            z.longitude = $lon,
            z.floor = $floor,
            z.updated_at = datetime()
        RETURN z
        """
        result = await self.session.run(
            query, code=code, name=name, total_spots=total_spots,
            occupied=occupied, lat=lat, lon=lon, floor=floor,
        )
        return await result.single()

    # ─── Zone Relationships ────────────────────────────────────────────

    async def connect_zones(self, code_a: str, code_b: str, distance_meters: float):
        """Create CONNECTED_TO relationship (bidirectional) with distance weight.

        Used for Dijkstra's shortest path routing.
        """
        query = """
        MATCH (a:Zone {code: $code_a}), (b:Zone {code: $code_b})
        MERGE (a)-[r:CONNECTED_TO]->(b)
        SET r.distance = $distance
        MERGE (b)-[r2:CONNECTED_TO]->(a)
        SET r2.distance = $distance
        RETURN r
        """
        await self.session.run(
            query, code_a=code_a, code_b=code_b, distance=distance_meters
        )

    async def add_entrance(self, entrance_name: str, zone_code: str, distance: float):
        """Connect an entrance point to the nearest zone."""
        query = """
        MERGE (e:Entrance {name: $entrance_name})
        WITH e
        MATCH (z:Zone {code: $zone_code})
        MERGE (e)-[r:LEADS_TO]->(z)
        SET r.distance = $distance
        RETURN e, z
        """
        await self.session.run(
            query, entrance_name=entrance_name,
            zone_code=zone_code, distance=distance,
        )

    # ─── Dijkstra's Shortest Path ──────────────────────────────────────

    async def find_nearest_available(
        self, entrance_name: str, min_available: int = 1
    ) -> List[Dict]:
        """Find nearest available zone from an entrance using Dijkstra's algorithm.

        Theory: Greedy algorithm that explores nodes in order of cumulative distance.
        Complexity: O((V + E) log V) with priority queue.

        Optimization: Only considers zones with available spots > min_available.
        """
        query = """
        MATCH (start:Entrance {name: $entrance})
        MATCH (target:Zone)
        WHERE target.available >= $min_available
        CALL apoc.algo.dijkstra(start, target, 'LEADS_TO|CONNECTED_TO', 'distance')
        YIELD path, weight
        RETURN target.code AS zone_code,
               target.name AS zone_name,
               target.available AS available_spots,
               weight AS distance_meters,
               [n IN nodes(path) | n.code] AS route
        ORDER BY weight ASC
        LIMIT 3
        """
        try:
            result = await self.session.run(
                query, entrance=entrance_name, min_available=min_available,
            )
            records = [record.data() async for record in result]
            return records
        except Exception as e:
            logger.error(f"Dijkstra query failed: {e}")
            # Fallback: simple distance-based query
            return await self._fallback_nearest(min_available)

    async def _fallback_nearest(self, min_available: int) -> List[Dict]:
        """Fallback: return zones ordered by available spots."""
        query = """
        MATCH (z:Zone)
        WHERE z.available >= $min_available
        RETURN z.code AS zone_code, z.name AS zone_name,
               z.available AS available_spots
        ORDER BY z.available DESC
        LIMIT 3
        """
        result = await self.session.run(query, min_available=min_available)
        return [record.data() async for record in result]

    # ─── Centrality Analysis ───────────────────────────────────────────

    async def compute_betweenness_centrality(self) -> List[Dict]:
        """Compute betweenness centrality to identify critical junction zones.

        Theory: BC(v) = Σ_{s≠v≠t} σ_{st}(v) / σ_{st}
        Zones with high BC are bottlenecks — losing them disrupts routing.
        """
        query = """
        CALL gds.betweenness.stream({
            nodeProjection: 'Zone',
            relationshipProjection: 'CONNECTED_TO'
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).code AS zone_code,
               gds.util.asNode(nodeId).name AS zone_name,
               score AS betweenness_centrality
        ORDER BY score DESC
        """
        try:
            result = await self.session.run(query)
            return [record.data() async for record in result]
        except Exception as e:
            logger.warning(f"GDS centrality not available: {e}")
            return []

    async def compute_pagerank(self) -> List[Dict]:
        """Rank zones by traffic flow importance using PageRank.

        Theory: PR(A) = (1-d) + d × Σ_{T∈B_A} PR(T) / C(T)
        where d=0.85, B_A = set of zones linking to A, C(T) = outgoing links of T.
        """
        query = """
        CALL gds.pageRank.stream({
            nodeProjection: 'Zone',
            relationshipProjection: 'CONNECTED_TO',
            dampingFactor: 0.85,
            maxIterations: 20
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).code AS zone_code,
               gds.util.asNode(nodeId).name AS zone_name,
               score AS pagerank
        ORDER BY score DESC
        """
        try:
            result = await self.session.run(query)
            return [record.data() async for record in result]
        except Exception as e:
            logger.warning(f"GDS PageRank not available: {e}")
            return []

    # ─── Community Detection ───────────────────────────────────────────

    async def detect_zone_communities(self) -> List[Dict]:
        """Group related zones using Louvain community detection.

        Theory: Optimizes modularity Q = (1/2m) Σ [Aᵢⱼ - kᵢkⱼ/2m] δ(cᵢ,cⱼ)
        Zones in the same community should be managed together.
        """
        query = """
        CALL gds.louvain.stream({
            nodeProjection: 'Zone',
            relationshipProjection: 'CONNECTED_TO'
        })
        YIELD nodeId, communityId
        RETURN gds.util.asNode(nodeId).code AS zone_code,
               communityId AS community
        ORDER BY communityId, zone_code
        """
        try:
            result = await self.session.run(query)
            return [record.data() async for record in result]
        except Exception as e:
            logger.warning(f"GDS Louvain not available: {e}")
            return []

    # ─── Spatial Queries ───────────────────────────────────────────────

    async def find_zones_within_radius(
        self, lat: float, lon: float, radius_meters: float
    ) -> List[Dict]:
        """Find zones within a radius using Haversine distance.

        d = 2r × arcsin(√(sin²(Δφ/2) + cos(φ₁)·cos(φ₂)·sin²(Δλ/2)))
        """
        query = """
        MATCH (z:Zone)
        WHERE z.latitude IS NOT NULL AND z.longitude IS NOT NULL
        WITH z,
             point({latitude: z.latitude, longitude: z.longitude}) AS zonePoint,
             point({latitude: $lat, longitude: $lon}) AS centerPoint
        WITH z, point.distance(zonePoint, centerPoint) AS dist
        WHERE dist <= $radius
        RETURN z.code AS zone_code, z.name AS zone_name,
               z.available AS available, round(dist) AS distance_meters
        ORDER BY dist ASC
        """
        result = await self.session.run(
            query, lat=lat, lon=lon, radius=radius_meters,
        )
        return [record.data() async for record in result]
