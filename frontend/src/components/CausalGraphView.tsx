import React, { useEffect, useState } from 'react';
import { CausalGraphData, CausalNode, CausalRelationshipType } from '../types';
import { api } from '../services/api';

interface CausalGraphViewProps {
  incidentId: string;
}

export const CausalGraphView: React.FC<CausalGraphViewProps> = ({ incidentId }) => {
  const [graphData, setGraphData] = useState<CausalGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.getGraph(incidentId)
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load causal graph data', err);
        setLoading(false);
      });
  }, [incidentId]);

  if (loading || !graphData) {
    return (
      <div className="p-8 text-center text-slate-400">
        Loading Causal Graph for {incidentId}...
      </div>
    );
  }

  const { nodes, edges } = graphData;

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const connectedEdges = edges.filter(
    (e) => e.source_id === selectedNodeId || e.target_id === selectedNodeId
  );

  const getRelationshipBadgeStyle = (rel: CausalRelationshipType) => {
    switch (rel) {
      case 'CAUSES':
        return 'bg-red-950 text-red-300 border-red-800';
      case 'CONTRIBUTES_TO':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      case 'SUPPORTS':
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'PRECEDES':
        return 'bg-blue-950 text-blue-300 border-blue-800';
      case 'CORRELATES_WITH':
        return 'bg-purple-950 text-purple-300 border-purple-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getNodeTypeBadgeStyle = (type: CausalNode['entity_type']) => {
    switch (type) {
      case 'event':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      case 'hypothesis':
        return 'bg-indigo-950 text-indigo-300 border-indigo-800';
      case 'evidence':
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'service':
        return 'bg-cyan-950 text-cyan-300 border-cyan-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Summary */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-lg flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Causal Relationship Graph
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Verified causal links, temporal precedents, and supporting evidence chains for {incidentId}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="bg-slate-950 border border-slate-800 px-2.5 py-1 rounded text-slate-300">
            Nodes: <span className="text-indigo-400 font-bold">{nodes.length}</span>
          </span>
          <span className="bg-slate-950 border border-slate-800 px-2.5 py-1 rounded text-slate-300">
            Edges: <span className="text-indigo-400 font-bold">{edges.length}</span>
          </span>
        </div>
      </div>

      {/* Main View Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Nodes Grid / Visual Graph representation */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Causal Nodes
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {nodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const nodeOutgoingEdges = edges.filter((e) => e.source_id === node.id);
              const nodeIncomingEdges = edges.filter((e) => e.target_id === node.id);

              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNodeId(isSelected ? null : node.id)}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-indigo-950/40 border-indigo-500 shadow-lg ring-1 ring-indigo-500'
                      : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold border ${getNodeTypeBadgeStyle(node.entity_type)}`}>
                      {node.entity_type.toUpperCase()}
                    </span>
                    <span className="text-xs font-mono text-slate-500">
                      ID: {node.id}
                    </span>
                  </div>

                  <h4 className="text-sm font-semibold text-slate-100 mb-2">
                    {node.name}
                  </h4>

                  {node.metadata && Object.keys(node.metadata).length > 0 && (
                    <div className="text-xs font-mono text-slate-400 bg-slate-950 p-2 rounded border border-slate-900 space-y-0.5 mb-2">
                      {Object.entries(node.metadata).map(([key, val]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-slate-500">{key}:</span>
                          <span className="text-slate-300">{String(val)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/60">
                    <span>In: {nodeIncomingEdges.length}</span>
                    <span>Out: {nodeOutgoingEdges.length}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Causal Edges List */}
          <div className="pt-4 space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Causal Edges & Evidence Links
            </h3>

            <div className="space-y-3">
              {edges.map((edge, idx) => {
                const sourceNode = nodes.find((n) => n.id === edge.source_id);
                const targetNode = nodes.find((n) => n.id === edge.target_id);

                return (
                  <div
                    key={idx}
                    className="p-4 bg-slate-900/70 border border-slate-800 rounded-lg space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap text-sm">
                        <span className="font-semibold text-slate-200">
                          {sourceNode?.name || edge.source_id}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded font-bold font-mono border ${getRelationshipBadgeStyle(edge.relationship)}`}>
                          ―― {edge.relationship} ➔
                        </span>
                        <span className="font-semibold text-slate-200">
                          {targetNode?.name || edge.target_id}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400">Supporting Evidence:</span>
                      {edge.evidence_ids.length > 0 ? (
                        edge.evidence_ids.map((evId) => (
                          <span
                            key={evId}
                            className="bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded font-mono font-bold"
                          >
                            {evId}
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-500 italic">None</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Sidebar: Inspector / Details */}
        <div className="space-y-4">
          <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-lg space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Node Inspector
            </h3>

            {selectedNode ? (
              <div className="space-y-4 text-xs">
                <div>
                  <span className="text-slate-500 block mb-1">Selected Node:</span>
                  <span className="text-slate-100 font-bold text-sm block">{selectedNode.name}</span>
                  <span className="text-slate-400 font-mono">ID: {selectedNode.id}</span>
                </div>

                <div>
                  <span className="text-slate-500 block mb-1">Type:</span>
                  <span className={`px-2 py-0.5 rounded font-mono font-bold border inline-block ${getNodeTypeBadgeStyle(selectedNode.entity_type)}`}>
                    {selectedNode.entity_type.toUpperCase()}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block mb-1">Connected Relationships:</span>
                  {connectedEdges.length === 0 ? (
                    <span className="text-slate-400 italic">No direct connections</span>
                  ) : (
                    <div className="space-y-2 mt-2">
                      {connectedEdges.map((edge, i) => (
                        <div key={i} className="p-2 bg-slate-950 rounded border border-slate-800">
                          <span className={`px-1.5 py-0.5 rounded font-mono font-bold text-[10px] border ${getRelationshipBadgeStyle(edge.relationship)}`}>
                            {edge.relationship}
                          </span>
                          <div className="text-slate-300 mt-1 font-mono">
                            {edge.source_id === selectedNode.id ? `➔ ${edge.target_id}` : ` ${edge.source_id}`}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded transition-colors"
                >
                  Clear Selection
                </button>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">
                Click any node in the list above to inspect its incoming and outgoing causal relationships and metadata.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
