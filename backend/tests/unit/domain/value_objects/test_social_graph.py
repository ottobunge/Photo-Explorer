"""Unit tests for SocialGraph value object."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.entities.face_cluster import FaceCluster
from app.domain.value_objects.face_relationship import FaceRelationship
from app.domain.value_objects.ids import FaceClusterId
from app.domain.value_objects.social_graph import SocialGraph


class TestSocialGraphCreation:
    """Test SocialGraph creation and initialization."""

    def test_social_graph_creation_with_empty_graph(self):
        """Test creating an empty social graph."""
        graph = SocialGraph(nodes=[], edges=[])

        assert graph.nodes == []
        assert graph.edges == []

    def test_social_graph_creation_with_nodes_and_edges(self):
        """Test creating social graph with nodes and edges."""
        cluster1 = FaceCluster.create()
        cluster2 = FaceCluster.create()

        relationship = FaceRelationship(
            person_a_id=cluster1.id.value,
            person_b_id=cluster2.id.value,
            shared_photo_count=5,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[cluster1, cluster2],
            edges=[relationship],
        )

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert cluster1 in graph.nodes
        assert cluster2 in graph.nodes
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
        cluster_a = FaceCluster.create()
        cluster_a.set_name("Alice")
        cluster_b = FaceCluster.create()
        cluster_b.set_name("Bob")
        cluster_c = FaceCluster.create()
        cluster_c.set_name("Charlie")
        cluster_d = FaceCluster.create()
        cluster_d.set_name("David")

        # Create relationships: A-B, A-C, B-C, D is isolated
        relationship_ab = FaceRelationship(
            person_a_id=cluster_a.id.value,
            person_b_id=cluster_b.id.value,
            shared_photo_count=5,
            sample_photo_ids=[],
        )
        relationship_ac = FaceRelationship(
            person_a_id=cluster_a.id.value,
            person_b_id=cluster_c.id.value,
            shared_photo_count=3,
            sample_photo_ids=[],
        )
        relationship_bc = FaceRelationship(
            person_a_id=cluster_b.id.value,
            person_b_id=cluster_c.id.value,
            shared_photo_count=2,
            sample_photo_ids=[],
        )

        # Full graph
        full_graph = SocialGraph(
            nodes=[cluster_a, cluster_b, cluster_c, cluster_d],
            edges=[relationship_ab, relationship_ac, relationship_bc],
        )

        # Filter to show only Alice's network
        alice_graph = full_graph.filter_by_person(cluster_a.id.value)

        # Should include A, B, C (all connected to A)
        assert len(alice_graph.nodes) == 3
        node_ids = {node.id.value for node in alice_graph.nodes}
        assert cluster_a.id.value in node_ids
        assert cluster_b.id.value in node_ids
        assert cluster_c.id.value in node_ids
        assert cluster_d.id.value not in node_ids

        # Should include edges A-B, A-C, B-C (all involving A's network)
        assert len(alice_graph.edges) == 3
        assert relationship_ab in alice_graph.edges
        assert relationship_ac in alice_graph.edges
        assert relationship_bc in alice_graph.edges

    def test_filter_by_isolated_person_returns_single_node(self):
        """Test filtering by person with no connections returns just that person."""
        cluster_a = FaceCluster.create()
        cluster_a.set_name("Alice")
        cluster_b = FaceCluster.create()
        cluster_b.set_name("Bob - Isolated")

        relationship = FaceRelationship(
            person_a_id=cluster_a.id.value,
            person_b_id=uuid4(),  # Relationship with someone not in graph
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[cluster_a, cluster_b],
            edges=[relationship],
        )

        # Filter by isolated person Bob
        bob_graph = graph.filter_by_person(cluster_b.id.value)

        # Should only include Bob (no connections)
        assert len(bob_graph.nodes) == 1
        assert bob_graph.nodes[0].id.value == cluster_b.id.value
        assert len(bob_graph.edges) == 0

    def test_filter_by_person_not_in_graph_returns_empty(self):
        """Test filtering by person not in graph returns empty graph."""
        cluster_a = FaceCluster.create()
        cluster_b = FaceCluster.create()

        relationship = FaceRelationship(
            person_a_id=cluster_a.id.value,
            person_b_id=cluster_b.id.value,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[cluster_a, cluster_b],
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
        cluster1 = FaceCluster.create()
        cluster2 = FaceCluster.create()
        cluster3 = FaceCluster.create()

        graph = SocialGraph(
            nodes=[cluster1, cluster2, cluster3],
            edges=[],
        )

        assert graph.node_count == 3

    def test_edge_count_property(self):
        """Test edge_count property returns correct count."""
        cluster1 = FaceCluster.create()
        cluster2 = FaceCluster.create()
        cluster3 = FaceCluster.create()

        relationship1 = FaceRelationship(
            person_a_id=cluster1.id.value,
            person_b_id=cluster2.id.value,
            shared_photo_count=1,
            sample_photo_ids=[],
        )
        relationship2 = FaceRelationship(
            person_a_id=cluster2.id.value,
            person_b_id=cluster3.id.value,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[cluster1, cluster2, cluster3],
            edges=[relationship1, relationship2],
        )

        assert graph.edge_count == 2

    def test_is_empty_property_for_empty_graph(self):
        """Test is_empty property returns True for empty graph."""
        graph = SocialGraph(nodes=[], edges=[])

        assert graph.is_empty is True

    def test_is_empty_property_for_non_empty_graph(self):
        """Test is_empty property returns False for non-empty graph."""
        cluster = FaceCluster.create()
        graph = SocialGraph(nodes=[cluster], edges=[])

        assert graph.is_empty is False

    def test_has_connections_property_for_graph_with_edges(self):
        """Test has_connections property returns True when graph has edges."""
        cluster1 = FaceCluster.create()
        cluster2 = FaceCluster.create()

        relationship = FaceRelationship(
            person_a_id=cluster1.id.value,
            person_b_id=cluster2.id.value,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[cluster1, cluster2],
            edges=[relationship],
        )

        assert graph.has_connections is True

    def test_has_connections_property_for_graph_without_edges(self):
        """Test has_connections property returns False when graph has no edges."""
        cluster = FaceCluster.create()
        graph = SocialGraph(nodes=[cluster], edges=[])

        assert graph.has_connections is False


class TestSocialGraphNodeRetrieval:
    """Test retrieving nodes from social graph."""

    def test_get_node_by_id_returns_correct_node(self):
        """Test get_node_by_id() returns the correct node."""
        cluster1 = FaceCluster.create()
        cluster1.set_name("Alice")
        cluster2 = FaceCluster.create()
        cluster2.set_name("Bob")

        graph = SocialGraph(
            nodes=[cluster1, cluster2],
            edges=[],
        )

        result = graph.get_node_by_id(cluster1.id.value)

        assert result is not None
        assert result.id.value == cluster1.id.value
        assert result.name == "Alice"

    def test_get_node_by_id_returns_none_for_unknown_id(self):
        """Test get_node_by_id() returns None for unknown ID."""
        cluster = FaceCluster.create()
        graph = SocialGraph(nodes=[cluster], edges=[])

        result = graph.get_node_by_id(uuid4())

        assert result is None

    def test_get_relationships_for_person(self):
        """Test get_relationships_for_person() returns all edges involving that person."""
        cluster_a = FaceCluster.create()
        cluster_b = FaceCluster.create()
        cluster_c = FaceCluster.create()

        relationship_ab = FaceRelationship(
            person_a_id=cluster_a.id.value,
            person_b_id=cluster_b.id.value,
            shared_photo_count=5,
            sample_photo_ids=[],
        )
        relationship_ac = FaceRelationship(
            person_a_id=cluster_a.id.value,
            person_b_id=cluster_c.id.value,
            shared_photo_count=3,
            sample_photo_ids=[],
        )
        relationship_bc = FaceRelationship(
            person_a_id=cluster_b.id.value,
            person_b_id=cluster_c.id.value,
            shared_photo_count=2,
            sample_photo_ids=[],
        )

        graph = SocialGraph(
            nodes=[cluster_a, cluster_b, cluster_c],
            edges=[relationship_ab, relationship_ac, relationship_bc],
        )

        # Get all relationships for Alice
        alice_relationships = graph.get_relationships_for_person(cluster_a.id.value)

        assert len(alice_relationships) == 2
        assert relationship_ab in alice_relationships
        assert relationship_ac in alice_relationships
        assert relationship_bc not in alice_relationships


class TestSocialGraphSerialization:
    """Test SocialGraph serialization."""

    def test_to_dict_serialization(self):
        """Test to_dict serialization."""
        cluster1 = FaceCluster.create()
        cluster1.set_name("Alice")
        cluster2 = FaceCluster.create()
        cluster2.set_name("Bob")

        relationship = FaceRelationship(
            person_a_id=cluster1.id.value,
            person_b_id=cluster2.id.value,
            shared_photo_count=5,
            sample_photo_ids=[uuid4(), uuid4()],
        )

        graph = SocialGraph(
            nodes=[cluster1, cluster2],
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
