"""Unit tests for SocialGraph value object."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.value_objects.face_relationship import FaceRelationship
from app.domain.value_objects.social_graph import ClusterNode, SocialGraph


def create_test_cluster_node(
    name: str | None = None,
    face_count: int = 1,
    representative_face_id: str | None = None,
) -> ClusterNode:
    """Create a test ClusterNode with sensible defaults."""
    return ClusterNode(
        id=uuid4(),
        name=name,
        face_count=face_count,
        representative_face_id=uuid4() if representative_face_id else None,
    )


class TestSocialGraphCreation:
    """Test SocialGraph creation and initialization."""

    def test_social_graph_creation_with_empty_graph(self):
        """Test creating an empty social graph."""
        graph = SocialGraph(nodes=[], edges=[])

        assert graph.nodes == []
        assert graph.edges == []

    def test_social_graph_creation_with_nodes_and_edges(self):
        """Test creating social graph with nodes and edges."""
        node1 = create_test_cluster_node(name="Alice")
        node2 = create_test_cluster_node(name="Bob")

        relationship = FaceRelationship(
            person_a_id=node1.id,
            person_b_id=node2.id,
            shared_photo_count=5,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[node1, node2],
            edges=[relationship],
        )

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert node1 in graph.nodes
        assert node2 in graph.nodes
        assert relationship in graph.edges

    def test_social_graph_is_immutable(self):
        """Test that SocialGraph is immutable (frozen dataclass)."""
        graph = SocialGraph(nodes=[], edges=[])

        with pytest.raises(AttributeError):
            graph.nodes = []  # Should raise error for frozen dataclass


class TestSocialGraphFiltering:
    """Test social graph filtering by person."""

    def test_filter_by_person_returns_direct_connections_only(self):
        """Test filtering graph to show only direct connections to a person."""
        # Create 4 people: A, B, C, D
        node_a = create_test_cluster_node(name="Alice")
        node_b = create_test_cluster_node(name="Bob")
        node_c = create_test_cluster_node(name="Charlie")
        node_d = create_test_cluster_node(name="David")

        # Create relationships: A-B, A-C, B-C, D is isolated
        relationship_ab = FaceRelationship(
            person_a_id=node_a.id,
            person_b_id=node_b.id,
            shared_photo_count=5,
            sample_photo_ids=[],
        )
        relationship_ac = FaceRelationship(
            person_a_id=node_a.id,
            person_b_id=node_c.id,
            shared_photo_count=3,
            sample_photo_ids=[],
        )
        relationship_bc = FaceRelationship(
            person_a_id=node_b.id,
            person_b_id=node_c.id,
            shared_photo_count=2,
            sample_photo_ids=[],
        )

        # Full graph
        full_graph = SocialGraph(
            nodes=[node_a, node_b, node_c, node_d],
            edges=[relationship_ab, relationship_ac, relationship_bc],
        )

        # Filter to show only Alice's network
        alice_graph = full_graph.filter_by_person(node_a.id)

        # Should include A, B, C (all connected to A)
        assert len(alice_graph.nodes) == 3
        node_ids = {node.id for node in alice_graph.nodes}
        assert node_a.id in node_ids
        assert node_b.id in node_ids
        assert node_c.id in node_ids
        assert node_d.id not in node_ids

        # Should include edges A-B, A-C, B-C (all involving A's network)
        assert len(alice_graph.edges) == 3
        assert relationship_ab in alice_graph.edges
        assert relationship_ac in alice_graph.edges
        assert relationship_bc in alice_graph.edges

    def test_filter_by_isolated_person_returns_single_node(self):
        """Test filtering by person with no connections returns just that person."""
        node_a = create_test_cluster_node(name="Alice")
        node_b = create_test_cluster_node(name="Bob - Isolated")

        relationship = FaceRelationship(
            person_a_id=node_a.id,
            person_b_id=uuid4(),  # Relationship with someone not in graph
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[node_a, node_b],
            edges=[relationship],
        )

        # Filter by isolated person Bob
        bob_graph = graph.filter_by_person(node_b.id)

        # Should only include Bob (no connections)
        assert len(bob_graph.nodes) == 1
        assert bob_graph.nodes[0].id == node_b.id
        assert len(bob_graph.edges) == 0

    def test_filter_by_person_not_in_graph_returns_empty(self):
        """Test filtering by person not in graph returns empty graph."""
        node_a = create_test_cluster_node()
        node_b = create_test_cluster_node()

        relationship = FaceRelationship(
            person_a_id=node_a.id,
            person_b_id=node_b.id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[node_a, node_b],
            edges=[relationship],
        )

        # Filter by person not in graph
        unknown_person_id = uuid4()
        filtered_graph = graph.filter_by_person(unknown_person_id)

        assert len(filtered_graph.nodes) == 0
        assert len(filtered_graph.edges) == 0


class TestSocialGraphProperties:
    """Test social graph computed properties."""

    def test_node_count_property(self):
        """Test node_count property returns correct count."""
        node1 = create_test_cluster_node()
        node2 = create_test_cluster_node()
        node3 = create_test_cluster_node()

        graph = SocialGraph(
            nodes=[node1, node2, node3],
            edges=[],
        )

        assert graph.node_count == 3

    def test_edge_count_property(self):
        """Test edge_count property returns correct count."""
        node1 = create_test_cluster_node()
        node2 = create_test_cluster_node()
        node3 = create_test_cluster_node()

        relationship1 = FaceRelationship(
            person_a_id=node1.id,
            person_b_id=node2.id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )
        relationship2 = FaceRelationship(
            person_a_id=node2.id,
            person_b_id=node3.id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[node1, node2, node3],
            edges=[relationship1, relationship2],
        )

        assert graph.edge_count == 2

    def test_is_empty_property_for_empty_graph(self):
        """Test is_empty property returns True for empty graph."""
        graph = SocialGraph(nodes=[], edges=[])

        assert graph.is_empty is True

    def test_is_empty_property_for_non_empty_graph(self):
        """Test is_empty property returns False for non-empty graph."""
        node = create_test_cluster_node()
        graph = SocialGraph(nodes=[node], edges=[])

        assert graph.is_empty is False

    def test_has_connections_property_for_graph_with_edges(self):
        """Test has_connections property returns True when graph has edges."""
        node1 = create_test_cluster_node()
        node2 = create_test_cluster_node()

        relationship = FaceRelationship(
            person_a_id=node1.id,
            person_b_id=node2.id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[node1, node2],
            edges=[relationship],
        )

        assert graph.has_connections is True

    def test_has_connections_property_for_graph_without_edges(self):
        """Test has_connections property returns False when graph has no edges."""
        node = create_test_cluster_node()
        graph = SocialGraph(nodes=[node], edges=[])

        assert graph.has_connections is False


class TestSocialGraphNodeRetrieval:
    """Test retrieving nodes from social graph."""

    def test_get_node_by_id_returns_correct_node(self):
        """Test get_node_by_id() returns the correct node."""
        node1 = create_test_cluster_node(name="Alice")
        node2 = create_test_cluster_node(name="Bob")

        graph = SocialGraph(
            nodes=[node1, node2],
            edges=[],
        )

        result = graph.get_node_by_id(node1.id)

        assert result is not None
        assert result.id == node1.id
        assert result.name == "Alice"

    def test_get_node_by_id_returns_none_for_unknown_id(self):
        """Test get_node_by_id() returns None for unknown ID."""
        node = create_test_cluster_node()
        graph = SocialGraph(nodes=[node], edges=[])

        result = graph.get_node_by_id(uuid4())

        assert result is None

    def test_get_relationships_for_person(self):
        """Test get_relationships_for_person() returns all edges involving that person."""
        node_a = create_test_cluster_node()
        node_b = create_test_cluster_node()
        node_c = create_test_cluster_node()

        relationship_ab = FaceRelationship(
            person_a_id=node_a.id,
            person_b_id=node_b.id,
            shared_photo_count=5,
            sample_photo_ids=[],
        )
        relationship_ac = FaceRelationship(
            person_a_id=node_a.id,
            person_b_id=node_c.id,
            shared_photo_count=3,
            sample_photo_ids=[],
        )
        relationship_bc = FaceRelationship(
            person_a_id=node_b.id,
            person_b_id=node_c.id,
            shared_photo_count=2,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[node_a, node_b, node_c],
            edges=[relationship_ab, relationship_ac, relationship_bc],
        )

        # Get all relationships for Alice
        alice_relationships = graph.get_relationships_for_person(node_a.id)

        assert len(alice_relationships) == 2
        assert relationship_ab in alice_relationships
        assert relationship_ac in alice_relationships
        assert relationship_bc not in alice_relationships


class TestSocialGraphSerialization:
    """Test SocialGraph serialization."""

    def test_to_dict_serialization(self):
        """Test to_dict serialization."""
        node1 = create_test_cluster_node(name="Alice")
        node2 = create_test_cluster_node(name="Bob")

        relationship = FaceRelationship(
            person_a_id=node1.id,
            person_b_id=node2.id,
            shared_photo_count=5,
            sample_photo_ids=[uuid4(), uuid4()],
        )

        graph = SocialGraph(
            nodes=[node1, node2],
            edges=[relationship],
        )

        result = graph.to_dict()

        assert "nodes" in result
        assert "edges" in result
        assert "node_count" in result
        assert "edge_count" in result
        assert "is_empty" in result
        assert "has_connections" in result

        assert result["node_count"] == 2
        assert result["edge_count"] == 1
        assert result["is_empty"] is False
        assert result["has_connections"] is True

        # Nodes should include IDs and names
        assert len(result["nodes"]) == 2
        node_names = {node["name"] for node in result["nodes"]}
        assert "Alice" in node_names
        assert "Bob" in node_names

        # Edges should be serialized
        assert len(result["edges"]) == 1
        assert result["edges"][0]["shared_photo_count"] == 5

    def test_to_dict_with_empty_graph(self):
        """Test to_dict serialization with empty graph."""
        graph = SocialGraph(nodes=[], edges=[])

        result = graph.to_dict()

        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["node_count"] == 0
        assert result["edge_count"] == 0
        assert result["is_empty"] is True
        assert result["has_connections"] is False
