const path = require('path');

module.exports = {
  entry: {
    catalogue: path.resolve(__dirname, 'heritrace/static/js/components/Catalogue/index.jsx'),
    deletedEntities: path.resolve(__dirname, 'heritrace/static/js/components/DeletedEntities/index.jsx'),
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
            presets: ['@babel/preset-env', '@babel/preset-react']
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
  // Per il development
  devtool: 'source-map',
  mode: process.env.NODE_ENV === 'production' ? 'production' : 'development'
};