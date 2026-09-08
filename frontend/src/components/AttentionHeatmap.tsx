import * as d3 from 'd3';
import { useEffect, useRef } from 'react';
import type { AttentionWeight } from '@/types/api';

interface Props {
  weights: AttentionWeight[];
  height?: number;
}

/** D3 bar chart of decoder attention across the 90-day lookback window. */
export function AttentionHeatmap({ weights, height = 180 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || weights.length === 0) return;

    const render = () => {
      const width = container.clientWidth;
      const margin = { top: 10, right: 8, bottom: 28, left: 40 };
      d3.select(container).selectAll('*').remove();

      const svg = d3
        .select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('role', 'img')
        .attr('aria-label', 'Attention weights over the 90 day lookback window');

      const x = d3
        .scaleBand<number>()
        .domain(weights.map((weight) => weight.lag_days))
        .range([margin.left, width - margin.right])
        .padding(0.12);

      const maxWeight = d3.max(weights, (weight) => weight.weight) ?? 1;
      const y = d3
        .scaleLinear()
        .domain([0, maxWeight])
        .range([height - margin.bottom, margin.top]);
      const color = d3.scaleSequential(d3.interpolateBuGn).domain([maxWeight, 0]);

      const tooltip = d3
        .select(container)
        .append('div')
        .attr('class', 'pointer-events-none absolute z-10 hidden rounded bg-navy px-2 py-1 text-xs text-white shadow');

      svg
        .append('g')
        .selectAll('rect')
        .data(weights)
        .join('rect')
        .attr('x', (weight) => x(weight.lag_days) ?? 0)
        .attr('y', (weight) => y(weight.weight))
        .attr('width', x.bandwidth())
        .attr('height', (weight) => height - margin.bottom - y(weight.weight))
        .attr('fill', (weight) => color(weight.weight))
        .on('mousemove', (event: MouseEvent, weight) => {
          const [px, py] = d3.pointer(event, container);
          tooltip
            .classed('hidden', false)
            .style('left', `${px + 12}px`)
            .style('top', `${py - 12}px`)
            .html(`Lag ${weight.lag_days}d<br/>weight ${weight.weight.toFixed(4)}`);
        })
        .on('mouseleave', () => tooltip.classed('hidden', true));

      svg
        .append('g')
        .attr('transform', `translate(0,${height - margin.bottom})`)
        .call(
          d3
            .axisBottom(x)
            .tickValues(weights.filter((weight) => weight.lag_days % 7 === 0).map((w) => w.lag_days))
            .tickFormat((lag) => `${lag}d`),
        )
        .attr('font-size', 10);

      svg
        .append('g')
        .attr('transform', `translate(${margin.left},0)`)
        .call(d3.axisLeft(y).ticks(4).tickFormat(d3.format('.3f')))
        .attr('font-size', 10);
    };

    render();
    const observer = new ResizeObserver(render);
    observer.observe(container);
    return () => observer.disconnect();
  }, [weights, height]);

  return <div ref={containerRef} className="relative w-full" />;
}
