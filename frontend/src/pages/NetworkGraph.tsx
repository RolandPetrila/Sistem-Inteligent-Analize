/**
 * B2: Knowledge Graph Visualizer — Retea de firme conectate.
 * Ruta: /network/:cui — vizualizare interactiva cu React Flow (@xyflow/react).
 */

import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ArrowLeft, Network, Loader2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

interface NetworkNode {
  id: string;
  label: string;
  type: string; // "company" | "person"
  status?: string; // "activ" | "inactiv"
  cui?: string;
  depth?: number;
  toxic?: boolean;
}

interface NetworkEdge {
  source: string;
  target: string;
  label?: string;
}

interface NetworkData {
  cui: string;
  company_name: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  stats?: Record<string, unknown>;
  error?: string;
}

const NODE_COLORS: Record<string, string> = {
  center: "#6366f1", // accent-primary
  active: "#22c55e", // verde
  inactive: "#ef4444", // rosu
  unknown: "#6b7280", // gri
  person: "#f59e0b", // amber pentru persoane
};

function buildFlowNodes(nodes: NetworkNode[]): Node[] {
  return nodes.map((n, i) => {
    const isCenter = n.depth === 0;
    const isCompany = n.type === "company";
    let color = NODE_COLORS.unknown;
    if (isCenter) color = NODE_COLORS.center;
    else if (n.toxic) color = NODE_COLORS.inactive;
    else if (!isCompany) color = NODE_COLORS.person;
    else if (n.status === "activ") color = NODE_COLORS.active;
    else if (n.status === "inactiv") color = NODE_COLORS.inactive;

    // Simple circle layout
    const angle = (i / Math.max(nodes.length - 1, 1)) * 2 * Math.PI;
    const radius = isCenter ? 0 : 220 + (n.depth || 1) * 80;
    return {
      id: n.id,
      position: {
        x: isCenter ? 300 : 300 + radius * Math.cos(angle),
        y: isCenter ? 200 : 200 + radius * Math.sin(angle),
      },
      data: {
        label: (
          <div className="text-center p-1 max-w-[100px]">
            <div className="text-[10px] font-semibold truncate">{n.label}</div>
            {n.cui && <div className="text-[9px] text-gray-400">{n.cui}</div>}
          </div>
        ),
      },
      style: {
        background: color + "33",
        border: `2px solid ${color}`,
        borderRadius: isCompany ? "8px" : "50%",
        minWidth: "80px",
        fontSize: "11px",
        color: "#fff",
      },
    };
  });
}

function buildFlowEdges(edges: NetworkEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.label || "",
    style: { stroke: "#4b5563", strokeWidth: 1.5 },
    labelStyle: { fontSize: 9, fill: "#9ca3af" },
    type: "straight",
  }));
}

export default function NetworkGraph() {
  const { cui } = useParams<{ cui: string }>();
  const [networkData, setNetworkData] = useState<NetworkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!cui) return;
    setLoading(true);
    // Find company by CUI first
    api
      .listCompanies({ search: cui, limit: 1 })
      .then((res) => {
        const company = res.companies?.[0];
        if (!company) throw new Error("Companie negasita");
        return api.getCompanyNetwork(company.id);
      })
      .then((data: NetworkData) => {
        setNetworkData(data);
        if (data.nodes?.length) {
          setNodes(buildFlowNodes(data.nodes));
          setEdges(buildFlowEdges(data.edges || []));
        }
      })
      .catch(() =>
        setNetworkData({
          cui: cui || "",
          company_name: "N/A",
          nodes: [],
          edges: [],
          error: "Eroare la incarcarea datelor de retea",
        }),
      )
      .finally(() => setLoading(false));
  }, [cui]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const original = networkData?.nodes.find((n) => n.id === node.id);
      if (original) setSelectedNode(original);
    },
    [networkData],
  );

  return (
    <div className="space-y-4 h-full">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to="/companies" className="text-gray-400 hover:text-white">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <Network className="w-5 h-5 text-accent-secondary" />
        <div>
          <h1 className="text-xl font-bold text-white">
            Retea Firme — {networkData?.company_name || cui}
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {networkData?.nodes.length || 0} noduri,{" "}
            {networkData?.edges.length || 0} conexiuni | BFS depth-3
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
        </div>
      ) : networkData?.error ? (
        <div className="card flex items-center gap-3 text-yellow-400">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <p>{networkData.error}</p>
        </div>
      ) : networkData?.nodes.length === 0 ? (
        <div className="card text-center py-12">
          <Network className="w-12 h-12 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-400">
            Nu exista date de retea pentru aceasta firma.
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Reteaua se populeaza dupa o analiza cu optiunea "Profil Complet".
          </p>
        </div>
      ) : (
        <div className="flex gap-4 h-[600px]">
          {/* Graph */}
          <div className="flex-1 bg-dark-card border border-dark-border rounded-xl overflow-hidden">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              colorMode="dark"
            >
              <Background color="#374151" gap={20} />
              <Controls />
              <MiniMap
                nodeColor={(n) =>
                  (n.style?.border as string)?.replace("2px solid ", "") ||
                  "#6366f1"
                }
                style={{ background: "#1a1a2e" }}
              />
            </ReactFlow>
          </div>

          {/* Sidebar */}
          <div className="w-64 space-y-3">
            {/* Legend */}
            <div className="card text-xs space-y-2">
              <h3 className="font-semibold text-white text-sm">Legenda</h3>
              {[
                { color: NODE_COLORS.center, label: "Firma analizata" },
                { color: NODE_COLORS.active, label: "Firma activa" },
                {
                  color: NODE_COLORS.inactive,
                  label: "Firma inactiva / toxica",
                },
                { color: NODE_COLORS.person, label: "Persoana" },
                { color: NODE_COLORS.unknown, label: "Status necunoscut" },
              ].map(({ color, label }) => (
                <div key={label} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded"
                    style={{ background: color }}
                  />
                  <span className="text-gray-400">{label}</span>
                </div>
              ))}
            </div>

            {/* Selected node info */}
            {selectedNode && (
              <div className="card space-y-2">
                <h3 className="font-semibold text-white text-sm">
                  Nod selectat
                </h3>
                <p className="text-xs text-gray-300 font-medium">
                  {selectedNode.label}
                </p>
                {selectedNode.cui && (
                  <p className="text-xs text-gray-500">
                    CUI: {selectedNode.cui}
                  </p>
                )}
                {selectedNode.status && (
                  <p className="text-xs text-gray-500">
                    Status: {selectedNode.status}
                  </p>
                )}
                {selectedNode.type && (
                  <p className="text-xs text-gray-500">
                    Tip: {selectedNode.type}
                  </p>
                )}
                {selectedNode.toxic && (
                  <p className="text-xs text-red-400 font-semibold">
                    ⚠ Nod toxic detectat
                  </p>
                )}
                {selectedNode.cui && (
                  <Link
                    to={`/companies`}
                    className="block text-xs text-accent-secondary hover:text-white mt-1"
                  >
                    → Cauta firma
                  </Link>
                )}
              </div>
            )}

            {/* Stats */}
            {networkData?.stats && (
              <div className="card text-xs space-y-1">
                <h3 className="font-semibold text-white text-sm">Statistici</h3>
                {Object.entries(networkData.stats).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-gray-500">{k}:</span>
                    <span className="text-gray-300">{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
