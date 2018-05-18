import { scaleLinear } from "d3-scale";
import { axisBottom, axisLeft } from "d3-axis";

const dataFont = "Lato"; // should be centralised

export const haveMaxesChanged = (scales, newMaxX, newMaxY) => {
  return newMaxX !== scales.x.domain()[1] || newMaxY !== scales.y.domain()[1];
}

const removeXAxis = (svg) => {
  svg.selectAll(".x.axis").remove();
};

const removeYAxis = (svg) => {
  svg.selectAll(".y.axis").remove();
};

export const drawAxes = (svg, chartGeom, scales, numTicks = {x: 5, y: 5}) => {
  removeXAxis(svg);
  svg.append("g")
    .attr("class", "x axis")
    .attr("transform", `translate(0,${chartGeom.height - chartGeom.spaceBottom})`)
    .style("font-family", dataFont)
    .style("font-size", "12px")
    .call(axisBottom(scales.x).ticks(numTicks.x));
  removeYAxis(svg);
  svg.append("g")
    .attr("class", "y axis")
    .attr("transform", `translate(${chartGeom.spaceLeft},0)`)
    .style("font-family", dataFont)
    .style("font-size", "12px")
    .call(axisLeft(scales.y).ticks(numTicks.y));
};
export const calcScales = (chartGeom, maxX, maxY) => {
  return {
    x: scaleLinear()
      .domain([0, maxX])
      .range([chartGeom.spaceLeft, chartGeom.width - chartGeom.spaceRight]),
    y: scaleLinear()
      .domain([0, maxY])
      .range([chartGeom.height - chartGeom.spaceBottom, chartGeom.spaceTop])
  }
}
