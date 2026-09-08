import * as d3 from 'd3';
import { useEffect, useRef } from 'react';
import type { HeatmapCell } from '@/types/api';

interface Props {
  cells: HeatmapCell[];
  stores: number[];
  families: string[];
  onExportRef?: (exporter: () => void) => void;
}

const CELL = 18;

/** 54-store x 33-category coverage heatmap (red = high uncertainty, green = confident). */
export function GridHeatmap({ cells, stores, families, onExportRef }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || cells.length === 0) return;

    const margin = { top: 10, right: 10, bottom: 12, left: 150 };
    const width = margin.left + stores.length * CELL + margin.right;
    const height = margin.top + families.length * CELL + margin.bottom;

    d3.select(container).selectAll('*').remove();

    const svg = d3
      .select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('role', 'img')
      .attr('aria-label', 'Store by category coverage probability heatmap');

    const x = d3.scaleBand<number>().domain(stores).range([margin.left, width - margin.right]);
    const y = d3.scaleBand<string>().domain(families).range([margin.top, height - margin.bottom]);
    const extent = d3.extent(cells, (cell) => cell.coverage_probability) as [number, number];
    const color = d3.scaleSequential(d3.interpolateRdYlGn).domain(extent);

    const tooltip = d3
      .select(container)
      .append('div')
      .attr('class', 'pointer-events-none absolute z-10 hidden rounded bg-navy px-2 py-1 text-xs text-white shadow');

    svg
      .append('g')
      .selectAll('rect')
      .data(cells)
      .join('rect')
      .attr('x', (cell) => x(cell.store_nbr) ?? 0)
      .attr('y', (cell) => y(cell.family) ?? 0)
      .attr('width', x.bandwidth() - 1)
      .attr('height', y.bandwidth() - 1)
      .attr('fill', (cell) => color(cell.coverage_probability))
      .on('mousemove', (event: MouseEvent, cell) => {
        const [px, py] = d3.pointer(event, container);
        tooltip
          .classed('hidden', false)
          .style('left', `${px + 14}px`)
          .style('top', `${py - 10}px`)
          .html(
            `Store #${cell.store_nbr} - ${cell.family}<br/>coverage ${(cell.coverage_probability * 100).toFixed(1)}%<br/>MAPE ${cell.mape.toFixed(2)}%`,
          );
      })
      .on('mouseleave', () => tooltip.classed('hidden', true));

    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).tickSize(0))
      .attr('font-size', 9)
      .call((group) => group.select('.domain').remove());

    if (onExportRef) {
      onExportRef(() => exportSvgAsPng(svg.node() as SVGSVGElement, width, height, 'store-category-heatmap.png'));
    }
  }, [cells, stores, families, onExportRef]);

  return <div ref={containerRef} className="relative overflow-x-auto" />;
}

export function exportSvgAsPng(svg: SVGSVGElement, width: number, height: number, filename: string): void {
  const serialized = new XMLSerializer().serializeToString(svg);
  const image = new Image();
  image.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width = width * 2;
    canvas.height = height * 2;
    const context = canvas.getContext('2d');
    if (!context) return;
    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.scale(2, 2);
    context.drawImage(image, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    });
  };
  image.src = `data:image/svg+xml;base64,${window.btoa(unescape(encodeURIComponent(serialized)))}`;
}
