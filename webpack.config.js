// SPDX-FileCopyrightText: 2024 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

const path = require('path');

module.exports = (_env, argv) => ({
  entry: {
    catalogue: path.resolve(__dirname, 'heritrace/static/js/components/Catalogue/index.jsx'),
    timeline: path.resolve(__dirname, 'heritrace/static/js/components/Timeline/index.jsx'),
    navigation: path.resolve(__dirname, 'heritrace/static/js/components/Navigation/index.jsx'),
  },
  output: {
    filename: '[name].bundle.js',
    path: path.resolve(__dirname, 'heritrace/static/dist'),
    publicPath: '/static/dist/'
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              '@babel/preset-env',
              ['@babel/preset-react', { development: argv.mode === 'development' }]
            ]
          }
        }
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx'],
    // Per permettere import relativi dalla directory components
    alias: {
      '@components': path.resolve(__dirname, 'heritrace/static/js/components')
    }
  },
  devtool: 'source-map',
  mode: argv.mode
});
