"""SocialGraph value object - Social network graph of face relationships."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.value_objects.face_relationship import FaceRelationship


@dataclass(frozen=True)
class ClusterNode:
    """Immutable cluster metadata for use in social graphs.

    This value object represents essential cluster information without
    maintaining a reference to the mutable FaceCluster entity.
    """

    id: UUID
    name: Optional[str]
    face_count: int
    representative_face_id: Optional[UUID]


@dataclass(frozen=True)
class SocialGraph:
    """
    Immutable social graph structure.

    Represents the complete social network of people (face clusters) and their
    relationships based on photo co-appearances.

    Uses immutable ClusterNode objects instead of mutable FaceCluster entities
    to ensure the value object contract is maintained.
    """

    nodes: list[ClusterNode]
    edges: list[FaceRelationship]

    @property
    def node_count(self) -> int:
        """Get the number of nodes (people) in the graph."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Get the number of edges (relationships) in the graph."""
        return len(self.edges)

    @property
    def is_empty(self) -> bool:
        """Check if the graph has no nodes."""
        return len(self.nodes) == 0

    @property
    def has_connections(self) -> bool:
        """Check if the graph has any relationships (edges)."""
        return len(self.edges) > 0

    def filter_by_person(self, person_id: UUID) -> "SocialGraph":
        """
        Return subgraph containing only direct connections to a person.

        Given a person ID, returns a new SocialGraph containing only that person
        and all people directly connected to them, along with all edges between
        those people.

        Args:
            person_id: The ID of the person to filter by.

        Returns:
            SocialGraph: Filtered subgraph showing only the person's network.
                        Always includes the target person, even if isolated.
        """
        # Find all edges involving this person
        relevant_edges = [
            edge for edge in self.edges
            if edge.involves(person_id)
        ]

        # Find all people connected via these edges
        # Always include the target person, even if they have no connections
        connected_person_ids: set[UUID] = {person_id}
        for edge in relevant_edges:
            connected_person_ids.add(edge.person_a_id)
            connected_person_ids.add(edge.person_b_id)

        # Filter nodes to only those in the connected set
        filtered_nodes = [
            node for node in self.nodes
            if node.id in connected_person_ids
        ]

        # Include all edges between nodes in the filtered set
        # This includes edges not directly involving the target person
        # but connecting their friends to each other
        filtered_edges = [
            edge for edge in self.edges
            if edge.person_a_id in connected_person_ids
            and edge.person_b_id in connected_person_ids
        ]

        return SocialGraph(nodes=filtered_nodes, edges=filtered_edges)

    def get_node_by_id(self, person_id: UUID) -> ClusterNode | None:
        """
        Get a node (person) by their ID.

        Args:
            person_id: The ID of the person to find.

        Returns:
            ClusterNode | None: The cluster node if found, None otherwise.
        """
        for node in self.nodes:
            if node.id == person_id:
                return node
        return None

    def get_relationships_for_person(self, person_id: UUID) -> list[FaceRelationship]:
        """
        Get all relationships (edges) involving a specific person.

        Args:
            person_id: The ID of the person.

        Returns:
            list[FaceRelationship]: All relationships involving this person.
        """
        return [
            edge for edge in self.edges
            if edge.involves(person_id)
        ]

    def to_dict(self) -> dict[str, object]:
        """
        Serialize SocialGraph to a dictionary.

        Returns:
            dict: Dictionary representation with nodes, edges, and computed properties.
        """
        return {
            "nodes": [self._serialize_node(node) for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "is_empty": self.is_empty,
            "has_connections": self.has_connections,
        }

    def _serialize_node(self, node: ClusterNode) -> dict[str, object]:
        """
        Serialize a cluster node to dictionary.

        Args:
            node: The cluster node to serialize.

        Returns:
            dict: Node representation with essential fields.
        """
        return {
            "id": str(node.id),
            "name": node.name,
            "face_count": node.face_count,
            "representative_face_id": str(node.representative_face_id) if node.representative_face_id else None,
        }
