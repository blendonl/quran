export interface ElongatedCharacter {
  original: string;
  displayed: string;
  repetitions: number;
  durationMs: number;
  isElongated: boolean;
}

export interface ElongationResult {
  originalText: string;
  displayText: string;
  characters: ElongatedCharacter[];
}
