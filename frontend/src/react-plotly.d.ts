declare module 'react-plotly.js' {
  import { Component } from 'react';
  import type { PlotlyHTMLElement } from 'plotly.js';

  interface Figure {
    data: any[];
    layout?: any;
    frames?: any[];
  }

  interface PlotParams {
    data: any[];
    layout?: any;
    frames?: any[];
    config?: any;
    onInitialized?: (figure: Figure, graphDiv: PlotlyHTMLElement) => void;
    onUpdate?: (figure: Figure, graphDiv: PlotlyHTMLElement) => void;
    onPurge?: (figure: Figure, graphDiv: PlotlyHTMLElement) => void;
    onError?: (error: Error) => void;
    [key: string]: any;
  }

  export default class Plot extends Component<PlotParams> {}
}
