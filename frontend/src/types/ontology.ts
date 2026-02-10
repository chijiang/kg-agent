export interface OntologyNode {
    name: string
    label?: string[] | string
    dataProperties?: string[]
    color?: string
}

export type Selection =
    | { type: 'node'; data: OntologyNode }
    | { type: 'edge'; data: { source: string; target: string; relationship_type: string } }
